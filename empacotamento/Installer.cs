using System;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Interop;
using System.Windows.Markup;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Shell;
using System.Windows.Threading;
using Microsoft.Win32;

// A standalone WPF frontend. The embedded backend owns installation transactions,
// upgrades, shortcuts and uninstall registration; it is never downloaded at runtime.
internal static class InstallerEngine {
    internal const string UninstallKey = @"Software\Microsoft\Windows\CurrentVersion\Uninstall\{C522DFD9-6BF4-4FE0-9CE4-5D3C5C88E470}_is1";
    internal static string Version { get { return Assembly.GetExecutingAssembly().GetCustomAttribute<AssemblyInformationalVersionAttribute>().InformationalVersion; } }

    internal static string ResourceText(string name) {
        using (Stream stream = Assembly.GetExecutingAssembly().GetManifestResourceStream(name))
        using (StreamReader reader = new StreamReader(stream)) return reader.ReadToEnd().Trim();
    }
    internal static string Quote(string value) {
        // CommandLineToArgvW escaping, including trailing backslashes.
        StringBuilder result = new StringBuilder("\""); int slashes = 0;
        foreach (char c in value) {
            if (c == '\\') { slashes++; continue; }
            if (c == '"') result.Append('\\', slashes * 2 + 1);
            else result.Append('\\', slashes);
            result.Append(c); slashes = 0;
        }
        return result.Append('\\', slashes * 2).Append('"').ToString();
    }
    internal static string Arguments(string[] args) {
        StringBuilder result = new StringBuilder();
        foreach (string arg in args) { if (result.Length > 0) result.Append(' '); result.Append(Quote(arg)); }
        return result.ToString();
    }
    internal static string ValidateDestination(string value) {
        if (String.IsNullOrWhiteSpace(value) || value.IndexOfAny(new char[] {'"', '\r', '\n', '\0'}) >= 0)
            throw new ArgumentException(InstallerText.T("invalid_folder"));
        if (!Path.IsPathRooted(value) || Path.GetPathRoot(value).Length < 3 || value.StartsWith(@"\\"))
            throw new ArgumentException(InstallerText.T("local_folder"));
        string full = Path.GetFullPath(value.Trim()).TrimEnd('\\', '/');
        string root = Path.GetPathRoot(full).TrimEnd('\\', '/');
        string windows = Environment.GetFolderPath(Environment.SpecialFolder.Windows).TrimEnd('\\');
        if (String.Equals(full, root, StringComparison.OrdinalIgnoreCase) || File.Exists(full) ||
            String.Equals(full, Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), StringComparison.OrdinalIgnoreCase) ||
            String.Equals(full, Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), StringComparison.OrdinalIgnoreCase) ||
            String.Equals(full, windows, StringComparison.OrdinalIgnoreCase) || full.StartsWith(windows + "\\", StringComparison.OrdinalIgnoreCase))
            throw new ArgumentException(InstallerText.T("system_folder"));
        return full;
    }
    internal static string DefaultDestination() {
        // Inno's original AppId is retained, so an upgrade reuses its destination.
        using (RegistryKey key = Registry.CurrentUser.OpenSubKey(UninstallKey)) {
            string previous = key == null ? null : key.GetValue("InstallLocation") as string;
            if (!String.IsNullOrWhiteSpace(previous)) {
                try { return ValidateDestination(previous); } catch (ArgumentException) { }
            }
        }
        return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "Onda");
    }
    internal static string NewSession() {
        string session = Path.Combine(Path.GetTempPath(), "OndaSetup-" + Guid.NewGuid().ToString("N"));
        DirectorySecurity security = new DirectorySecurity();
        security.SetAccessRuleProtection(true, false);
        InheritanceFlags inheritance = InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit;
        security.AddAccessRule(new FileSystemAccessRule(WindowsIdentity.GetCurrent().User,
            FileSystemRights.FullControl, inheritance, PropagationFlags.None, AccessControlType.Allow));
        security.AddAccessRule(new FileSystemAccessRule(new SecurityIdentifier(WellKnownSidType.LocalSystemSid, null),
            FileSystemRights.FullControl, inheritance, PropagationFlags.None, AccessControlType.Allow));
        if (Directory.Exists(session)) throw new IOException(InstallerText.T("temp_failed"));
        Directory.CreateDirectory(session, security);
        return session;
    }
    internal static string ExtractBackend(string session) {
        string file = Path.Combine(session, "engine.exe");
        using (Stream source = Assembly.GetExecutingAssembly().GetManifestResourceStream("Onda.InstallEngine"))
        using (FileStream target = new FileStream(file, FileMode.CreateNew, FileAccess.Write, FileShare.None)) source.CopyTo(target);
        string actual;
        using (SHA256 hash = SHA256.Create())
        using (FileStream source = File.OpenRead(file)) actual = BitConverter.ToString(hash.ComputeHash(source)).Replace("-", "").ToLowerInvariant();
        if (actual != ResourceText("Onda.EngineHash")) throw new InvalidDataException(InstallerText.T("incomplete"));
        return file;
    }
    internal static int Execute(string backend, string[] args) {
        ProcessStartInfo start = new ProcessStartInfo(backend, Arguments(args));
        start.UseShellExecute = false; start.CreateNoWindow = true;
        start.WorkingDirectory = Path.GetDirectoryName(backend);
        using (Process child = Process.Start(start)) { child.WaitForExit(); return child.ExitCode; }
    }
    internal static void Cleanup(string session) {
        // Remove only our known files, and only from our own GUID session directory.
        if (String.IsNullOrEmpty(session)) return;
        string full = Path.GetFullPath(session);
        string parent = Path.GetFullPath(Path.GetTempPath()).TrimEnd('\\');
        Guid id;
        if (!String.Equals(Path.GetDirectoryName(full), parent, StringComparison.OrdinalIgnoreCase) ||
            !Path.GetFileName(full).StartsWith("OndaSetup-") ||
            !Guid.TryParseExact(Path.GetFileName(full).Substring(10), "N", out id)) return;
        foreach (string name in new string[] {"engine.exe", "progress.txt", "install.log"}) {
            try { File.Delete(Path.Combine(full, name)); } catch (IOException) { } catch (UnauthorizedAccessException) { }
        }
        try { Directory.Delete(full); } catch (IOException) { } catch (UnauthorizedAccessException) { }
    }
    internal static bool Silent(string[] args) {
        foreach (string arg in args) if (String.Equals(arg, "/VERYSILENT", StringComparison.OrdinalIgnoreCase) ||
            String.Equals(arg, "/SILENT", StringComparison.OrdinalIgnoreCase)) return true;
        return false;
    }
}

internal sealed class InstallerWindow {
    internal readonly Window Window;
    private readonly TextBox destination;
    private readonly CheckBox shortcut;
    private readonly Button action;
    private readonly DispatcherTimer timer;
    private bool busy, completed, restartRequired;
    private volatile string session;
    private string logPath, installedDirectory;
    private int lastProgress;
    private string currentState = "configure";
    internal InstallerWindow() {
        using (Stream source = Assembly.GetExecutingAssembly().GetManifestResourceStream("Onda.InstallerView"))
            Window = (Window)XamlReader.Load(source);
        WindowChrome.SetWindowChrome(Window, new WindowChrome { CaptionHeight = 0, ResizeBorderThickness = new Thickness(6), GlassFrameThickness = new Thickness(0), CornerRadius = new CornerRadius(22) });
        Rect area = SystemParameters.WorkArea;
        Window.MinWidth = Math.Min(Window.MinWidth, Math.Max(640, area.Width - 32));
        Window.MinHeight = Math.Min(Window.MinHeight, Math.Max(480, area.Height - 32));
        Window.Width = Math.Max(Window.MinWidth, Math.Min(Window.Width, area.Width - 32));
        Window.Height = Math.Max(Window.MinHeight, Math.Min(Window.Height, area.Height - 32));
        destination = Find<TextBox>("DestinationBox"); shortcut = Find<CheckBox>("ShortcutBox"); action = Find<Button>("InstallButton");
        destination.Text = InstallerEngine.DefaultDestination();
        Find<TextBlock>("VersionLabel").Text = InstallerEngine.Version;
        Find<Button>("CloseButton").Click += delegate { Window.Close(); };
        Find<Button>("MinimizeButton").Click += delegate { Window.WindowState = WindowState.Minimized; };
        Find<Grid>("TitleBar").MouseLeftButtonDown += delegate(object sender, System.Windows.Input.MouseButtonEventArgs e) {
            if (e.OriginalSource is TextBlock || e.OriginalSource == sender) Window.DragMove();
        };
        Find<Button>("BrowseButton").Click += delegate {
            using (System.Windows.Forms.FolderBrowserDialog picker = new System.Windows.Forms.FolderBrowserDialog()) {
                picker.Description = InstallerText.T("folder_dialog"); picker.SelectedPath = destination.Text;
                if (picker.ShowDialog(new NativeOwner(new WindowInteropHelper(Window).Handle)) == System.Windows.Forms.DialogResult.OK) destination.Text = picker.SelectedPath;
            }
        };
        Find<Button>("DetailsButton").Click += delegate {
            if (!String.IsNullOrEmpty(logPath) && File.Exists(logPath)) Process.Start(new ProcessStartInfo("notepad.exe", InstallerEngine.Quote(logPath)) { UseShellExecute = false });
        };
        action.Click += async delegate { await Activate(); };
        Window.Closing += delegate(object sender, System.ComponentModel.CancelEventArgs e) {
            if (busy) { e.Cancel = true; Message(InstallerText.T("wait"), false); }
        };
        Window.KeyDown += delegate(object sender, System.Windows.Input.KeyEventArgs e) {
            if (e.Key == System.Windows.Input.Key.Escape && !busy) Window.Close();
        };
        timer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(200) };
        timer.Tick += delegate { ReadProgress(); };
        ComboBox languages = Find<ComboBox>("LanguagePicker");
        foreach (ComboBoxItem item in languages.Items) if ((string)item.Tag == InstallerText.Language) languages.SelectedItem = item;
        languages.SelectionChanged += delegate {
            ComboBoxItem selected = languages.SelectedItem as ComboBoxItem;
            if (selected == null) return;
            InstallerText.Language = (string)selected.Tag;
            Find<TextBlock>("MessageLabel").Visibility = Visibility.Collapsed;
            ApplyLanguage();
        };
        ApplyLanguage();
    }
    internal void ApplyLanguage() {
        Window.Title = InstallerText.T("title");
        Find<TextBlock>("LanguageLabel").Text = InstallerText.T("language");
        System.Windows.Automation.AutomationProperties.SetName(Find<ComboBox>("LanguagePicker"), InstallerText.T("language"));
        System.Windows.Automation.AutomationProperties.SetName(Find<Button>("MinimizeButton"), InstallerText.T("minimize"));
        System.Windows.Automation.AutomationProperties.SetName(Find<Button>("CloseButton"), InstallerText.T("close"));
        System.Windows.Automation.AutomationProperties.SetName(Find<Button>("BrowseButton"), InstallerText.T("browse"));
        System.Windows.Automation.AutomationProperties.SetName(destination, InstallerText.T("destination_a11y"));
        ((System.Windows.Documents.Run)Window.FindName("HeroPrefix")).Text = InstallerText.T("hero_prefix");
        ((System.Windows.Documents.Run)Window.FindName("HeroSuffix")).Text = InstallerText.T("hero_suffix");
        Find<TextBlock>("Subtitle").Text = InstallerText.T("subtitle");
        Find<Label>("DestinationLabel").Content = InstallerText.T("destination");
        shortcut.Content = InstallerText.T("shortcut");
        Find<TextBlock>("PlatformLabel").Text = InstallerText.T("platform");
        Find<Button>("DetailsButton").Content = InstallerText.T("details");
        Find<TextBlock>("Footnote").Text = InstallerText.T("footnote");
        Find<TextBlock>("ConfigureStep").Text = InstallerText.T("step_configure");
        Find<TextBlock>("InstallStep").Text = InstallerText.T("step_install");
        Find<TextBlock>("CompleteStep").Text = InstallerText.T("step_done");
        Find<TextBlock>("ProgressText").Text = InstallerText.T("preparing");
        SetState(currentState);
        if (restartRequired) { action.Content = InstallerText.T("finish"); Message(InstallerText.T("restart"), false); }
    }
    internal T Find<T>(string name) where T : FrameworkElement { return (T)Window.FindName(name); }
    private void Message(string text, bool error) {
        TextBlock label = Find<TextBlock>("MessageLabel"); label.Text = text;
        label.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString(error ? "#FFB6AE" : "#B8C9CF"));
        label.Visibility = Visibility.Visible;
    }
    internal void SetState(string state) {
        currentState = state;
        bool installing = state == "installing", done = state == "done";
        Find<ComboBox>("LanguagePicker").IsEnabled = !installing;
        Find<StackPanel>("OptionsPanel").Visibility = installing || done ? Visibility.Collapsed : Visibility.Visible;
        Find<StackPanel>("ProgressPanel").Visibility = installing ? Visibility.Visible : Visibility.Collapsed;
        Find<TextBlock>("PageHeading").Text = installing ? InstallerText.T("heading_installing") : done ? InstallerText.T("heading_done") : InstallerText.T("heading_configure");
        action.Content = done ? InstallerText.T("open") : InstallerText.T("install"); action.IsEnabled = !installing;
        Find<TextBlock>("ConfigureStep").Foreground = new SolidColorBrush(installing || done ? Colors.LightSlateGray : Color.FromRgb(121,226,196));
        Find<TextBlock>("InstallStep").Foreground = new SolidColorBrush(installing ? Color.FromRgb(121,226,196) : Colors.LightSlateGray);
        Find<TextBlock>("CompleteStep").Foreground = new SolidColorBrush(done ? Color.FromRgb(121,226,196) : Colors.LightSlateGray);
        if (done) Message(InstallerText.T("done"), false);
    }
    private void ReadProgress() {
        if (session == null) return;
        try {
            string[] parts = File.ReadAllText(Path.Combine(session, "progress.txt")).Trim().Split('/');
            int current, total;
            if (parts.Length == 2 && Int32.TryParse(parts[0], out current) && Int32.TryParse(parts[1], out total) && total > 0) {
                lastProgress = Math.Max(lastProgress, Math.Min(99, (int)(current * 99.0 / total)));
                Find<ProgressBar>("InstallProgress").IsIndeterminate = false;
                Find<ProgressBar>("InstallProgress").Value = lastProgress;
                Find<TextBlock>("PercentLabel").Text = lastProgress.ToString(CultureInfo.InvariantCulture) + "%";
                Find<TextBlock>("ProgressText").Text = lastProgress >= 99 ? InstallerText.T("finalizing") : InstallerText.T("installing_files");
            }
        } catch (IOException) { } catch (UnauthorizedAccessException) { }
    }
    private async Task Activate() {
        if (busy) return;
        if (completed) {
            if (restartRequired) { Window.Close(); return; }
            try {
                Process.Start(new ProcessStartInfo(Path.Combine(installedDirectory, "Onda.exe")) { UseShellExecute = true, WorkingDirectory = installedDirectory });
                Window.Close();
            } catch (Exception error) { Message(InstallerText.T("open_failed", error.Message), true); }
            return;
        }
        try { installedDirectory = InstallerEngine.ValidateDestination(destination.Text); }
        catch (Exception error) { Message(error.Message, true); destination.Focus(); return; }
        bool createShortcut = shortcut.IsChecked == true;
        string backendLanguage = InstallerText.BackendLanguage;
        busy = true; lastProgress = 0; SetState("installing");
        Find<TextBlock>("MessageLabel").Visibility = Visibility.Collapsed;
        Find<TextBlock>("PercentLabel").Text = "0%";
        Find<TextBlock>("ProgressText").Text = InstallerText.T("preparing");
        Find<ProgressBar>("InstallProgress").Value = 0;
        Find<ProgressBar>("InstallProgress").IsIndeterminate = true;
        Find<Button>("DetailsButton").Visibility = Visibility.Collapsed;
        timer.Start();
        try {
            int code = await Task.Run(delegate {
                session = InstallerEngine.NewSession();
                string backend = InstallerEngine.ExtractBackend(session);
                return InstallerEngine.Execute(backend, new string[] { "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/RESTARTEXITCODE=3010", "/SP-",
                    "/LANG="+backendLanguage, "/DIR="+installedDirectory, createShortcut ? "/TASKS=desktopicon" : "/TASKS=", "/ONDAPROGRESS="+Path.Combine(session,"progress.txt"), "/LOG="+Path.Combine(session,"install.log") });
            });
            if (code != 0 && code != 3010) throw new InvalidOperationException(InstallerText.T("install_failed", code));
            if (!File.Exists(Path.Combine(installedDirectory, "Onda.exe"))) throw new IOException(InstallerText.T("missing_launcher"));
            completed = true; SetState("done");
            if (code == 3010) { restartRequired = true; action.Content = InstallerText.T("finish"); Message(InstallerText.T("restart"), false); }
        } catch (Exception error) { SetState("configure"); Message(error.Message, true); }
        finally {
            timer.Stop(); busy = false; PreserveLog(); InstallerEngine.Cleanup(session); session = null;
        }
    }
    private void PreserveLog() {
        if (session == null || !File.Exists(Path.Combine(session,"install.log"))) return;
        try {
            string folder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Onda", "installer-logs");
            Directory.CreateDirectory(folder);
            logPath = Path.Combine(folder, "install-"+DateTime.UtcNow.ToString("yyyyMMdd-HHmmss")+"-"+Guid.NewGuid().ToString("N").Substring(0,8)+".log");
            File.Copy(Path.Combine(session,"install.log"), logPath);
            Find<Button>("DetailsButton").Visibility = Visibility.Visible;
        } catch (IOException) { } catch (UnauthorizedAccessException) { }
    }
    internal void Render(string path, string state) {
        SetState(state);
        if (state == "installing") {
            Find<ProgressBar>("InstallProgress").Value = 63; Find<TextBlock>("PercentLabel").Text = "63%";
            Find<TextBlock>("ProgressText").Text = InstallerText.T("installing_files");
        }
        FrameworkElement content = (FrameworkElement)Window.Content;
        content.Width = 1040; content.Height = 660;
        content.Measure(new Size(1040,660)); content.Arrange(new Rect(0,0,1040,660)); content.UpdateLayout();
        RenderTargetBitmap bitmap = new RenderTargetBitmap(1560,990,144,144,PixelFormats.Pbgra32); bitmap.Render(content);
        PngBitmapEncoder encoder = new PngBitmapEncoder(); encoder.Frames.Add(BitmapFrame.Create(bitmap));
        using (FileStream file = File.Create(path)) encoder.Save(file);
    }
    private sealed class NativeOwner : System.Windows.Forms.IWin32Window {
        public IntPtr Handle { get; private set; }
        public NativeOwner(IntPtr handle) { Handle = handle; }
    }
}

internal static class InstallerProgram {
    [STAThread]
    private static int Main(string[] args) {
        string session = null;
        try {
            string[] visibleArgs = InstallerText.SelectFromArguments(args);
            if (InstallerEngine.Silent(args)) {
                session = InstallerEngine.NewSession();
                return InstallerEngine.Execute(InstallerEngine.ExtractBackend(session), InstallerText.BackendArguments(args));
            }
            args = visibleArgs;
            Application app = new Application();
            InstallerWindow view = new InstallerWindow();
            if (args.Length >= 2 && args[0] == "--render-preview") {
                view.Render(args[1], args.Length > 2 ? args[2] : "configure"); return 0;
            }
            if (args.Length == 2 && args[0] == "--self-test") {
                if (!InstallerEngine.Silent(new string[] {"/verysilent"}) || InstallerEngine.Silent(new string[0])) throw new Exception("Silent dispatch failed.");
                if (InstallerEngine.Quote("a\\\"b\\") != "\"a\\\\\\\"b\\\\\"") throw new Exception("Argument escaping failed.");
                bool rejected = false;
                try { InstallerEngine.ValidateDestination(Path.GetPathRoot(Environment.SystemDirectory)); } catch (ArgumentException) { rejected = true; }
                if (!rejected) throw new Exception("Unsafe destination accepted.");
                session = InstallerEngine.NewSession(); InstallerEngine.ExtractBackend(session);
                int keys = InstallerText.Validate();
                string selectedFolder = view.Find<TextBox>("DestinationBox").Text;
                view.Find<CheckBox>("ShortcutBox").IsChecked = false;
                foreach (ComboBoxItem item in view.Find<ComboBox>("LanguagePicker").Items) {
                    view.Find<ComboBox>("LanguagePicker").SelectedItem = item;
                    view.SetState("configure");
                    if (view.Window.Title != InstallerText.T("title") ||
                        (string)view.Find<Button>("InstallButton").Content != InstallerText.T("install") ||
                        view.Find<TextBox>("DestinationBox").Text != selectedFolder ||
                        view.Find<CheckBox>("ShortcutBox").IsChecked != false) throw new Exception("Language switch lost installer state.");
                    try { InstallerEngine.ValidateDestination(" "); throw new Exception("Invalid folder accepted."); }
                    catch (ArgumentException error) { if (error.Message != InstallerText.T("invalid_folder")) throw; }
                    if (!InstallerText.T("install_failed", 7).Contains("7")) throw new Exception("Error code placeholder lost.");
                    if (InstallerText.Normalize(InstallerText.BackendLanguage) != InstallerText.Language ||
                        InstallerText.BackendArguments(new string[] {"/LANG="+InstallerText.Language})[0] != "/LANG="+InstallerText.BackendLanguage) throw new Exception("Backend language mapping failed.");
                    view.SetState("installing");
                    if (view.Find<ComboBox>("LanguagePicker").IsEnabled || view.Find<Button>("InstallButton").IsEnabled ||
                        view.Find<TextBlock>("PageHeading").Text != InstallerText.T("heading_installing")) throw new Exception("Installing translation failed.");
                    view.SetState("done");
                    if ((string)view.Find<Button>("InstallButton").Content != InstallerText.T("open") ||
                        view.Find<TextBlock>("MessageLabel").Text != InstallerText.T("done")) throw new Exception("Completion translation failed.");
                }
                File.WriteAllText(args[1], "{\"ok\":true,\"version\":\"" + InstallerEngine.Version + "\",\"embedded_backend_verified\":true,\"languages\":[\"pt-BR\",\"es\",\"en\"],\"translation_keys\":"+keys+",\"language_switch_preserves_options\":true}"); return 0;
            }
            if (args.Length != 0) throw new ArgumentException(InstallerText.T("arguments"));
            using (Mutex mutex = new Mutex(false, @"Local\Onda.CustomInstaller")) {
                bool owned;
                try { owned = mutex.WaitOne(0); } catch (AbandonedMutexException) { owned = true; }
                if (!owned) { MessageBox.Show(InstallerText.T("already_open"), "ONDA"); return 1; }
                try { app.Run(view.Window); } finally { mutex.ReleaseMutex(); }
            }
            return 0;
        } catch (Exception error) {
            if (args.Length > 0 && args[0].StartsWith("--")) {
                try { File.WriteAllText(args[1]+".error.txt", error.ToString()); } catch { }
            } else MessageBox.Show(error.Message, InstallerText.T("title"), MessageBoxButton.OK, MessageBoxImage.Error);
            return 1;
        } finally { InstallerEngine.Cleanup(session); }
    }
}
