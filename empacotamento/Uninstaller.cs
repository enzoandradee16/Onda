using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Threading;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Interop;
using System.Windows.Markup;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Shell;
using Microsoft.Win32;

internal static class RemoveEngine {
    internal const string Frontend = "Desinstalar ONDA.exe";
#if ONDA_AUDIT
    internal const string RegistryPath = @"Software\Microsoft\Windows\CurrentVersion\Uninstall\{190D43B2-9B31-47EE-A14D-94DB3A2EC850}_is1";
#else
    internal const string RegistryPath = InstallerEngine.UninstallKey;
#endif
    internal static string Hash(string path) {
        using (SHA256 hash = SHA256.Create())
        using (Stream source = File.OpenRead(path)) return BitConverter.ToString(hash.ComputeHash(source)).Replace("-", "").ToLowerInvariant();
    }
    internal static string Validate(string directory) {
        string full = InstallerEngine.ValidateDestination(directory);
        for (DirectoryInfo part = new DirectoryInfo(full); part != null; part = part.Parent)
            if ((part.Attributes & FileAttributes.ReparsePoint) != 0) throw new InvalidDataException(InstallerText.T("u_invalid"));
        using (RegistryKey key = Registry.CurrentUser.OpenSubKey(RegistryPath)) {
            string registered = key == null ? null : key.GetValue("InstallLocation") as string;
            if (String.IsNullOrEmpty(registered) || !String.Equals(Path.GetFullPath(registered).TrimEnd('\\'), full, StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException(InstallerText.T("u_invalid"));
        }
        string stamp = Path.Combine(full, "uninstall-engine.sha256");
        string[] expected = File.ReadAllLines(stamp);
        if (expected.Length != 3 || !Regex.IsMatch(expected[0],@"^unins[0-9]+\.exe$") || expected[1] != Hash(Path.Combine(full, expected[0])) || expected[2] != Hash(Path.ChangeExtension(Path.Combine(full,expected[0]),"dat")) ||
            Hash(Assembly.GetExecutingAssembly().Location) != Hash(Path.Combine(full, Frontend)))
            throw new InvalidDataException(InstallerText.T("u_invalid"));
        return full;
    }
    internal static string[] Command(string directory, bool data, bool tools, string language, string session) {
        return new string[] { "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/ONDACUSTOM=1",
            "/ONDADATA="+(data ? "1" : "0"), "/ONDATOOLS="+(tools ? "1" : "0"), "/LANG="+language,
            "/LOG="+Path.Combine(session,"uninstall.log"), "/ONDAPROGRESS="+Path.Combine(session,"progress.txt") };
    }
    internal static int Remove(string directory, bool data, bool tools, string language, string session) {
        directory = Validate(directory);
        string backend=Path.Combine(directory,File.ReadAllLines(Path.Combine(directory,"uninstall-engine.sha256"))[0]);
        int code = InstallerEngine.Execute(backend, Command(directory,data,tools,language,session));
        if (code != 0 && code != 3010) throw new IOException(InstallerText.T("u_exit",code));
        // Inno's bootstrap launches a detached copy; wait for its completion marker.
        string progress = Path.Combine(session,"progress.txt");
        DateTime deadline = DateTime.UtcNow.AddSeconds(120);
        while (DateTime.UtcNow < deadline) {
            string marker="";
            try{if(File.Exists(progress))marker=File.ReadAllText(progress).Trim();}catch(IOException){}
            if(marker=="cleanup_failed")throw new IOException(InstallerText.T("u_partial"));
            if (marker == "complete") {
                if (File.Exists(Path.Combine(directory,"Onda.exe"))) throw new IOException(InstallerText.T("u_incomplete"));
                return code;
            }
            System.Threading.Thread.Sleep(100);
        }
        throw new IOException(InstallerText.T("u_incomplete"));
    }
    internal static void Cleanup(string session) {
        string parent = Path.GetFullPath(Path.GetTempPath()).TrimEnd('\\');
        Guid id;
        if (!String.Equals(Path.GetDirectoryName(session),parent,StringComparison.OrdinalIgnoreCase) ||
            !Path.GetFileName(session).StartsWith("OndaSetup-") || !Guid.TryParseExact(Path.GetFileName(session).Substring(10),"N",out id)) return;
        // This small detached helper deletes only the private copy after we exit.
        // The log stays available for diagnosis; no recursive deletion is used.
        string copy = Path.Combine(session,"uninstaller.exe").Replace("'","''");
        string script = "Wait-Process -Id "+Process.GetCurrentProcess().Id+" -ErrorAction SilentlyContinue; Remove-Item -LiteralPath '"+copy+"' -ErrorAction SilentlyContinue";
        try { Process.Start(new ProcessStartInfo(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System), @"WindowsPowerShell\v1.0\powershell.exe"),
            "-NoProfile -NonInteractive -WindowStyle Hidden -Command "+InstallerEngine.Quote(script)) {UseShellExecute=false,CreateNoWindow=true}); }
        catch (Exception) { /* Private temp cleanup never changes the uninstall result. */ }
    }
}

internal sealed class UninstallerWindow {
    internal readonly Window Window;
    private readonly string directory, session;
    private bool busy, done;
    internal bool Succeeded;
    private string state = "configure";
    internal T Find<T>(string name) where T : FrameworkElement {return (T)Window.FindName(name);}
    internal UninstallerWindow(string directory, string session) {
        this.directory=directory;this.session=session;
        using (Stream source=Assembly.GetExecutingAssembly().GetManifestResourceStream("Onda.UninstallerView")) Window=(Window)XamlReader.Load(source);
        WindowChrome.SetWindowChrome(Window,new WindowChrome {CaptionHeight=0,ResizeBorderThickness=new Thickness(6),GlassFrameThickness=new Thickness(0),CornerRadius=new CornerRadius(22)});
        Rect area=SystemParameters.WorkArea;
        Window.MinWidth=Math.Min(Window.MinWidth,Math.Max(640,area.Width-32));Window.MinHeight=Math.Min(Window.MinHeight,Math.Max(480,area.Height-32));
        Window.Width=Math.Min(Window.Width,area.Width-32);Window.Height=Math.Min(Window.Height,area.Height-32);
        Find<TextBox>("DestinationBox").Text=directory;
        Find<TextBlock>("VersionLabel").Text=InstallerEngine.Version;
        Find<Button>("CloseButton").Click+=delegate {Window.Close();};
        Find<Button>("MinimizeButton").Click+=delegate {Window.WindowState=WindowState.Minimized;};
        Find<Button>("CancelButton").Click+=delegate {Window.Close();};
        Find<Button>("DetailsButton").Click+=delegate {
            string log=Path.Combine(session,"uninstall.log");
            if(File.Exists(log))Process.Start(new ProcessStartInfo("notepad.exe",InstallerEngine.Quote(log)){UseShellExecute=false});
        };
        Find<Grid>("TitleBar").MouseLeftButtonDown+=delegate(object sender,System.Windows.Input.MouseButtonEventArgs e) {
            if(e.OriginalSource is TextBlock || e.OriginalSource==sender)Window.DragMove();
        };
        Window.Closing+=delegate(object sender,System.ComponentModel.CancelEventArgs e){if(busy)e.Cancel=true;};
        Window.KeyDown+=delegate(object sender,System.Windows.Input.KeyEventArgs e){if(e.Key==System.Windows.Input.Key.Escape && !busy)Window.Close();};
        Find<Button>("UninstallButton").Click+=async delegate {await Activate();};
        ComboBox languages=Find<ComboBox>("LanguagePicker");
        foreach(ComboBoxItem item in languages.Items)if((string)item.Tag==InstallerText.Language)languages.SelectedItem=item;
        languages.SelectionChanged+=delegate {
            ComboBoxItem item=languages.SelectedItem as ComboBoxItem;
            if(item!=null){InstallerText.Language=(string)item.Tag;ApplyLanguage();}
        };
        ApplyLanguage();
    }
    internal void ApplyLanguage() {
        Window.Title=InstallerText.T("u_title");
        ((System.Windows.Documents.Run)Window.FindName("HeroPrefix")).Text=InstallerText.T("u_prefix");
        ((System.Windows.Documents.Run)Window.FindName("HeroSuffix")).Text=InstallerText.T("u_suffix");
        foreach(string pair in new string[]{"LanguageLabel:language","Subtitle:u_subtitle","DescriptionLabel:u_description","SafetyLabel:u_safety","ProgressText:u_progress","ConfigureStep:u_confirm_step","InstallStep:u_remove_step","CompleteStep:u_done_step"}) {
            string[] parts=pair.Split(':');Find<TextBlock>(parts[0]).Text=InstallerText.T(parts[1]);
        }
        Find<Label>("DestinationLabel").Content=InstallerText.T("u_folder");
        Find<CheckBox>("DeleteDataBox").Content=InstallerText.T("u_data");
        Find<CheckBox>("DeleteToolsBox").Content=InstallerText.T("u_tools");
        foreach(string name in new string[]{"DeleteDataBox","DeleteToolsBox"})Find<CheckBox>(name).ToolTip=InstallerText.T("u_shared");
        Find<Button>("CancelButton").Content=InstallerText.T("u_cancel");
        Find<Button>("DetailsButton").Content=InstallerText.T("details");
        System.Windows.Automation.AutomationProperties.SetName(Find<ComboBox>("LanguagePicker"),InstallerText.T("language"));
        System.Windows.Automation.AutomationProperties.SetName(Find<Button>("CloseButton"),InstallerText.T("u_close"));
        System.Windows.Automation.AutomationProperties.SetName(Find<Button>("MinimizeButton"),InstallerText.T("u_minimize"));
        SetState(state);
    }
    internal void SetState(string value) {
        state=value;bool removing=value=="removing",complete=value=="done";
        Find<TextBlock>("PageHeading").Text=InstallerText.T(removing?"u_removing":complete?"u_done":"u_heading");
        Find<StackPanel>("OptionsPanel").Visibility=removing||complete?Visibility.Collapsed:Visibility.Visible;
        Find<StackPanel>("ProgressPanel").Visibility=removing?Visibility.Visible:Visibility.Collapsed;
        Find<ComboBox>("LanguagePicker").IsEnabled=!removing;
        Find<Button>("UninstallButton").IsEnabled=!removing;
        Find<Button>("UninstallButton").Content=InstallerText.T(complete?"u_finish":"u_action");
        Find<Button>("CancelButton").Visibility=complete?Visibility.Collapsed:Visibility.Visible;
        Find<Button>("CancelButton").IsEnabled=!removing;
        foreach(string name in new string[]{"ConfigureStep","InstallStep","CompleteStep"})
            Find<TextBlock>(name).Foreground=new SolidColorBrush(name==(complete?"CompleteStep":removing?"InstallStep":"ConfigureStep")?Color.FromRgb(121,226,196):Colors.LightSlateGray);
        if(complete)Message(InstallerText.T("u_finished"),false);
    }
    private void Message(string text,bool error) {
        Find<TextBlock>("MessageLabel").Text=text;
        Find<TextBlock>("MessageLabel").Foreground=new SolidColorBrush(error?Color.FromRgb(255,182,174):Color.FromRgb(184,201,207));
        Find<TextBlock>("MessageLabel").Visibility=Visibility.Visible;
    }
    internal async Task Activate() {
        if(busy)return;if(done){Window.Close();return;}
        bool data=Find<CheckBox>("DeleteDataBox").IsChecked==true,tools=Find<CheckBox>("DeleteToolsBox").IsChecked==true;
        string language=InstallerText.BackendLanguage;
        busy=true;Succeeded=false;SetState("removing");Find<TextBlock>("MessageLabel").Visibility=Visibility.Collapsed;Find<Button>("DetailsButton").Visibility=Visibility.Collapsed;
        try {
            int code=await Task.Run(delegate{return RemoveEngine.Remove(directory,data,tools,language,session);});
            Succeeded=true;done=true;SetState("done");if(code==3010)Message(InstallerText.T("u_restart"),false);
        } catch(Exception error){done=!File.Exists(Path.Combine(directory,"Onda.exe"));SetState(done?"done":"configure");Message(InstallerText.T("u_error",error.Message),true);if(File.Exists(Path.Combine(session,"uninstall.log")))Find<Button>("DetailsButton").Visibility=Visibility.Visible;}
        finally{busy=false;}
    }
}

internal static class UninstallerProgram {
    [STAThread] private static int Main(string[] raw) {
        string session=null;Mutex mutex=null;bool owned=false;
        try {
            if(raw.Length==0 || !raw[0].StartsWith("--self-test") && !raw[0].StartsWith("--render-preview")) {
                using(RegistryKey key=Registry.CurrentUser.OpenSubKey(RemoveEngine.RegistryPath)) {
                    string saved=key==null?null:key.GetValue("OndaUninstallLanguage") as string;
                    if(saved!=null)try{InstallerText.Language=InstallerText.Normalize(saved);}catch(ArgumentException){}
                }
            }
            string[] args=InstallerText.SelectFromArguments(raw);
            if(args.Length>0 && (args[0]=="--self-test" || args[0]=="--render-preview")) {
                Application app=new Application();app.ShutdownMode=ShutdownMode.OnExplicitShutdown;
                UninstallerWindow view=new UninstallerWindow(@"%LOCALAPPDATA%\Programs\Onda",null);
                if(args[0]=="--self-test") {
                    int count=InstallerText.Validate();
                    foreach(string language in InstallerText.Languages) {
                        InstallerText.Language=language;view.ApplyLanguage();
                        if(view.Find<CheckBox>("DeleteDataBox").IsChecked!=false || view.Find<CheckBox>("DeleteToolsBox").IsChecked!=false)throw new Exception("Unsafe defaults");
                        if((string)view.Find<Button>("UninstallButton").Content!=InstallerText.T("u_action"))throw new Exception("Translation error");
                        foreach(string state in new string[]{"removing","done","configure"})view.SetState(state);
                    }
                    view.Find<CheckBox>("DeleteDataBox").IsChecked=true;
                    foreach(string language in InstallerText.Languages){InstallerText.Language=language;view.ApplyLanguage();if(view.Find<CheckBox>("DeleteDataBox").IsChecked!=true || view.Find<CheckBox>("DeleteToolsBox").IsChecked!=false)throw new Exception("Language switch lost options");}
                    File.WriteAllText(args[1],"{\"ok\":true,\"languages\":[\"pt-BR\",\"es\",\"en\"],\"translation_keys\":"+count+",\"keeps_data_and_tools_by_default\":true}",Encoding.UTF8);
                } else {
                    if(args.Length>2)view.SetState(args[2]);view.Window.Show();view.Window.UpdateLayout();
                    RenderTargetBitmap bitmap=new RenderTargetBitmap((int)view.Window.ActualWidth,(int)view.Window.ActualHeight,96,96,PixelFormats.Pbgra32);
                    bitmap.Render(view.Window);PngBitmapEncoder encoder=new PngBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(bitmap));
                    using(Stream target=File.Create(args[1]))encoder.Save(target);
                }
                view.Window.Close();app.Shutdown();return 0;
            }
            string location=Assembly.GetExecutingAssembly().Location;
            bool relay=args.Length>=3 && args[0]=="--relay";
            string directory=RemoveEngine.Validate(relay?args[1]:Path.GetDirectoryName(location));
            if(!relay) {
                session=InstallerEngine.NewSession();string copy=Path.Combine(session,"uninstaller.exe");File.Copy(location,copy);
                List<string> forwarded=new List<string>{"--relay",directory,session,"/LANG="+InstallerText.BackendLanguage};forwarded.AddRange(args);
                Process.Start(new ProcessStartInfo(copy,InstallerEngine.Arguments(forwarded.ToArray())){UseShellExecute=false});
                session=null;return 0;
            }
            session=Path.GetDirectoryName(location);
            if(!String.Equals(session,args[2],StringComparison.OrdinalIgnoreCase) || !Path.GetFileName(location).Equals("uninstaller.exe",StringComparison.OrdinalIgnoreCase))throw new InvalidDataException(InstallerText.T("u_invalid"));
            mutex=new Mutex(false,"Local\\Onda.CustomUninstaller."+Regex.Replace(RemoveEngine.RegistryPath,"[^A-Za-z0-9]",""));
            try{owned=mutex.WaitOne(0);}catch(AbandonedMutexException){owned=true;}
            if(!owned)throw new IOException(InstallerText.T("u_already"));
#if ONDA_AUDIT
            int cancelIndex=Array.IndexOf(args,"--audit-ui-cancel");
            if(cancelIndex>=0) {
                Application cancelApp=new Application();UninstallerWindow cancelView=new UninstallerWindow(directory,session);
                cancelView.Window.ContentRendered+=delegate{cancelView.Find<Button>("CancelButton").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));};
                cancelApp.Run(cancelView.Window);File.WriteAllText(args[cancelIndex+1],"{\"ok\":true,\"cancelled\":true}");return 0;
            }
            int index=Array.IndexOf(args,"--audit-remove");
            if(index>=0) {
                string report=args[index+1];int code=RemoveEngine.Remove(directory,Array.IndexOf(args,"--remove-data")>=0,Array.IndexOf(args,"--remove-tools")>=0,InstallerText.BackendLanguage,session);
                File.WriteAllText(report,"{\"ok\":true,\"exit_code\":"+code+"}",Encoding.UTF8);return code;
            }
            index=Array.IndexOf(args,"--audit-ui-remove");
            if(index>=0) {
                string report=args[index+1];Application testApp=new Application();UninstallerWindow testView=new UninstallerWindow(directory,session);
                testView.Window.ContentRendered+=async delegate {
                    testView.Find<CheckBox>("DeleteDataBox").IsChecked=Array.IndexOf(args,"--remove-data")>=0;
                    testView.Find<CheckBox>("DeleteToolsBox").IsChecked=Array.IndexOf(args,"--remove-tools")>=0;
                    await testView.Activate();
                    File.WriteAllText(report,"{\"ok\":"+(testView.Succeeded?"true":"false")+",\"ui_worker\":true,\"message_base64\":\""+Convert.ToBase64String(Encoding.UTF8.GetBytes(testView.Find<TextBlock>("MessageLabel").Text))+"\"}");testApp.Shutdown();
                };
                testApp.Run(testView.Window);return 0;
            }
#endif
            if(args.Length!=3)throw new ArgumentException("Unsupported uninstaller argument");
            Application application=new Application();UninstallerWindow window=new UninstallerWindow(directory,session);application.Run(window.Window);return 0;
        } catch(Exception error){
#if ONDA_AUDIT
            int auditIndex=Array.IndexOf(raw,"--audit-remove");
            if(auditIndex<0)auditIndex=Array.IndexOf(raw,"--audit-ui-remove");
            if(auditIndex<0)auditIndex=Array.IndexOf(raw,"--audit-ui-cancel");
            if(auditIndex>=0 && raw.Length>auditIndex+1){File.WriteAllText(raw[auditIndex+1],"{\"ok\":false,\"error_base64\":\""+Convert.ToBase64String(Encoding.UTF8.GetBytes(error.ToString()))+"\"}");return 1;}
#endif
            MessageBox.Show(error.Message,InstallerText.T("u_title"),MessageBoxButton.OK,MessageBoxImage.Error);return 1;
        }
        finally{if(owned)mutex.ReleaseMutex();if(mutex!=null)mutex.Dispose();if(session!=null)RemoveEngine.Cleanup(session);}
    }
}
