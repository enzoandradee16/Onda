// Own WebView2 profile; passwords are entered only into the Instagram website.
using System;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Security.Cryptography;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Diagnostics;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

class InstagramSession : Form {
    readonly WebView2 browser = new WebView2();
    readonly Label status = new Label();
    readonly Button use = new Button();
    readonly Button install = new Button();
    readonly Button retry = new Button();
    readonly string root, language, action;
    bool saved;
    string T(string pt, string en, string es) { return language == "en" ? en : language == "es" ? es : pt; }
    InstagramSession(string[] args) {
        root = Path.GetFullPath(args[0]); language = args[1]; action = args[5];
        try { Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath); } catch { }
        Text = T("Conectar ao Instagram", "Connect to Instagram", "Conectar a Instagram");
        Width = 1040; Height = 820; MinimumSize = new Size(600, 500); StartPosition = FormStartPosition.CenterScreen;
        BackColor = ColorTranslator.FromHtml(args[2]); ForeColor = ColorTranslator.FromHtml(args[3]);
        Font = new Font("Segoe UI", 10);
        var footer = new FlowLayoutPanel { Dock = DockStyle.Bottom, AutoSize = true, MinimumSize = new Size(0, 52), Padding = new Padding(8), FlowDirection = FlowDirection.RightToLeft };
        use.Text = T("Usar esta sessão", "Use this session", "Usar esta sesión"); use.AutoSize = true;
        use.BackColor = ColorTranslator.FromHtml(args[4]); use.ForeColor = use.BackColor.GetBrightness() < .5f ? Color.White : Color.Black; use.FlatStyle = FlatStyle.Flat; use.Enabled = false;
        use.Click += async (s,e) => await Save(); footer.Controls.Add(use);
        retry.Text = T("Já instalei · Tentar novamente", "Installed · Try again", "Ya instalado · Reintentar"); retry.AutoSize = true; retry.Visible = false;
        retry.Click += async (s,e) => { retry.Enabled = false; await Initialize(); if (!IsDisposed) retry.Enabled = true; }; footer.Controls.Add(retry);
        install.Text = T("Instalar WebView2", "Install WebView2", "Instalar WebView2"); install.AutoSize = true; install.Visible = false;
        install.Click += (s,e) => {
            try {
                Process.Start(new ProcessStartInfo("https://go.microsoft.com/fwlink/p/?LinkId=2124703") { UseShellExecute = true });
                status.Text = T("Execute o instalador oficial da Microsoft baixado no navegador. Depois clique em Já instalei · Tentar novamente.", "Run the official Microsoft installer downloaded in your browser. Then click Installed · Try again.", "Ejecuta el instalador oficial de Microsoft descargado en el navegador. Después pulsa Ya instalado · Reintentar.");
            } catch { status.Text = T("Não foi possível abrir o navegador. Instale o WebView2 Runtime pelo site da Microsoft e tente novamente.", "Could not open your browser. Install WebView2 Runtime from Microsoft's website and try again.", "No se pudo abrir el navegador. Instala WebView2 Runtime desde Microsoft y reintenta."); }
        }; footer.Controls.Add(install);
        var close = new Button {Text = T("Fechar", "Close", "Cerrar"), AutoSize = true}; close.Click += (s,e) => Close(); footer.Controls.Add(close);
        status.Text = T("Entre no Instagram, conclua a verificação e clique em Usar esta sessão.", "Sign in to Instagram, complete verification, then click Use this session.", "Inicia sesión en Instagram, completa la verificación y pulsa Usar esta sesión.");
        status.Dock = DockStyle.Top; status.Height = 62; status.Padding = new Padding(12);
        browser.Dock = DockStyle.Fill; Controls.Add(browser); Controls.Add(status); Controls.Add(footer);
        Shown += async (s,e) => await Initialize();
        FormClosed += (s,e) => { browser.Dispose(); Environment.ExitCode = saved ? 0 : 2; };
        if (action == "disconnect" || action == "self-test") { Opacity = 0; ShowInTaskbar = false; }
    }
    static bool Allowed(string value) {
        Uri uri; if (!Uri.TryCreate(value, UriKind.Absolute, out uri) || uri.Scheme != "https") return false;
        return new [] {"instagram.com", "facebook.com", "meta.com"}.Any(d => uri.Host == d || uri.Host.EndsWith("." + d, StringComparison.OrdinalIgnoreCase));
    }
    async Task Initialize() {
        try {
            CoreWebView2Environment.GetAvailableBrowserVersionString();
            install.Visible = retry.Visible = false;
            Directory.CreateDirectory(root);
            var env = await CoreWebView2Environment.CreateAsync(null, Path.Combine(root, "profile"));
            await browser.EnsureCoreWebView2Async(env);
            browser.Visible = use.Visible = true;
            status.Height = 62;
            status.Text = T("Entre no Instagram, conclua a verificação e clique em Usar esta sessão.", "Sign in to Instagram, complete verification, then click Use this session.", "Inicia sesión en Instagram, completa la verificación y pulsa Usar esta sesión.");
            browser.CoreWebView2.Settings.AreDevToolsEnabled = false;
            browser.CoreWebView2.Settings.AreDefaultContextMenusEnabled = false;
            browser.CoreWebView2.Settings.IsPasswordAutosaveEnabled = false;
            browser.CoreWebView2.Settings.IsGeneralAutofillEnabled = false;
            if (action == "disconnect") {
                await browser.CoreWebView2.Profile.ClearBrowsingDataAsync(CoreWebView2BrowsingDataKinds.AllProfile);
                foreach (var name in new [] {"instagram-session.txt", "instagram-session.dpapi", "instagram-session.txt.tmp", "instagram-session.dpapi.tmp"}) {
                    var file = Path.Combine(root, name); if (File.Exists(file)) File.Delete(file);
                }
                saved = true; Close(); return;
            }
            if (action == "self-test") {
                var manager = browser.CoreWebView2.CookieManager;
                var cookie = manager.CreateCookie("onda_probe", "synthetic", "example.com", "/"); cookie.IsHttpOnly = true; cookie.IsSecure = true;
                manager.AddOrUpdateCookie(cookie);
                var rows = await manager.GetCookiesAsync("https://example.com/");
                saved = rows.Any(c => c.Name == "onda_probe" && c.Value == "synthetic" && c.IsHttpOnly);
                manager.DeleteCookiesWithDomainAndPath("onda_probe", "example.com", "/");
                WriteSession("# Netscape HTTP Cookie File\n.instagram.com\tTRUE\t/\tTRUE\t0\tsessionid\tsynthetic-only\n");
                File.WriteAllText(Path.Combine(root,"self-test.json"), saved ? "{\"ok\":true}" : "{\"ok\":false}"); Close(); return;
            }
            browser.CoreWebView2.NavigationStarting += (s,e) => { if (!Allowed(e.Uri)) e.Cancel = true; };
            browser.CoreWebView2.NewWindowRequested += (s,e) => { e.Handled = true; if (Allowed(e.Uri)) browser.CoreWebView2.Navigate(e.Uri); };
            browser.CoreWebView2.DownloadStarting += (s,e) => e.Cancel = true;
            browser.CoreWebView2.PermissionRequested += (s,e) => e.State = CoreWebView2PermissionState.Deny;
            browser.CoreWebView2.Navigate("https://www.instagram.com/accounts/login/"); use.Enabled = true;
        } catch (WebView2RuntimeNotFoundException) {
            if (action != "connect") { Close(); return; }
            browser.Visible = false;
            status.Height = 110;
            use.Visible = false;
            install.Visible = retry.Visible = true;
            status.Text = T("O login do Instagram precisa do Microsoft Edge WebView2 Runtime. Clique em Instalar WebView2 para baixar o instalador oficial da Microsoft.", "Instagram sign-in needs Microsoft Edge WebView2 Runtime. Click Install WebView2 to download Microsoft's official installer.", "El acceso a Instagram requiere Microsoft Edge WebView2 Runtime. Pulsa Instalar WebView2 para descargar el instalador oficial de Microsoft.");
        } catch {
            MessageBox.Show(T("Não foi possível iniciar o navegador integrado. Tente abrir a conexão novamente.", "Could not start the embedded browser. Try opening the connection again.", "No se pudo iniciar el navegador integrado. Intenta abrir la conexión de nuevo."), "ONDA"); Close();
        }
    }
    void WriteSession(string text) {
            string file = Path.Combine(root,"instagram-session.dpapi"), temp = file + ".tmp";
            byte[] clear = Encoding.UTF8.GetBytes(text);
            try {
                byte[] encrypted = ProtectedData.Protect(clear,null,DataProtectionScope.CurrentUser);
                using (var stream = new FileStream(temp,FileMode.Create,FileAccess.Write,FileShare.None)) {
                    var header = Encoding.ASCII.GetBytes("ONDA-IG-DPAPI\0"); stream.Write(header,0,header.Length); stream.Write(encrypted,0,encrypted.Length);
                }
            } finally { Array.Clear(clear,0,clear.Length); }
            if (File.Exists(file)) File.Replace(temp,file,null); else File.Move(temp,file);
            var legacy = Path.Combine(root,"instagram-session.txt"); if (File.Exists(legacy)) File.Delete(legacy);
    }
    async Task Save() {
        use.Enabled = false;
        try {
            var cookies = await browser.CoreWebView2.CookieManager.GetCookiesAsync("https://www.instagram.com/");
            var rows = cookies.Where(c => (c.Domain.TrimStart('.') == "instagram.com" || c.Domain.EndsWith(".instagram.com")) && !String.IsNullOrEmpty(c.Value)).ToList();
            if (!rows.Any(c => c.Name == "sessionid") || !rows.Any(c => c.Name == "ds_user_id")) {
                status.Text = T("O login ainda não foi concluído. Entre na conta e aguarde o Instagram carregar.", "Sign-in is not complete. Sign in and wait for Instagram to load.", "El inicio de sesión no se ha completado. Accede y espera a que cargue Instagram."); return;
            }
            var text = new StringBuilder("# Netscape HTTP Cookie File\n");
            foreach (var c in rows) {
                if (new [] {c.Name,c.Value,c.Domain,c.Path}.Any(v => v.IndexOfAny(new [] {'\t','\r','\n'}) >= 0)) throw new InvalidDataException();
                long expiry = c.IsSession ? 0 : Math.Max(0, (long)(c.Expires.ToUniversalTime() - new DateTime(1970,1,1,0,0,0,DateTimeKind.Utc)).TotalSeconds);
                text.Append(c.IsHttpOnly ? "#HttpOnly_" : "").Append(c.Domain).Append('\t').Append(c.Domain.StartsWith(".") ? "TRUE" : "FALSE").Append('\t').Append(c.Path).Append('\t').Append(c.IsSecure ? "TRUE" : "FALSE").Append('\t').Append(expiry.ToString(CultureInfo.InvariantCulture)).Append('\t').Append(c.Name).Append('\t').Append(c.Value).Append('\n');
            }
            WriteSession(text.ToString());
            saved = true; Close();
        } catch { status.Text = T("Não foi possível salvar a sessão. Tente novamente.", "Could not save the session. Try again.", "No se pudo guardar la sesión. Inténtalo de nuevo."); }
        finally { if (!IsDisposed) use.Enabled = true; }
    }
    [STAThread] static void Main(string[] args) {
        if (args.Length != 6) { Environment.ExitCode = 1; return; }
        Application.EnableVisualStyles(); Application.Run(new InstagramSession(args));
    }
}
