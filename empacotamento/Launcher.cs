using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Windows.Forms;

[assembly: AssemblyTitle("Onda")]
[assembly: AssemblyProduct("Onda")]
[assembly: AssemblyVersion("1.1.4.0")]
[assembly: AssemblyFileVersion("1.1.4.0")]
[assembly: AssemblyInformationalVersion("1.1.4")]

internal static class Launcher {
    private static string Quote(string value) {
        return "\"" + value.Replace("\"", "\\\"") + "\"";
    }
    private static string T(string pt, string en, string es) {
        try {
            string path = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Onda", "language.json");
            string language = File.ReadAllText(path).Trim().Trim('"');
            if (language == "en") return en;
            if (language == "es") return es;
        } catch { }
        return pt;
    }
    [STAThread]
    private static int Main(string[] args) {
        try {
            string root = AppDomain.CurrentDomain.BaseDirectory;
            string python = Path.Combine(root, "_runtime", "python", "pythonw.exe");
            string entry = Path.Combine(root, "Onda", "desktop_entry.py");
            if (!File.Exists(python) || !File.Exists(entry)) {
                MessageBox.Show(T("O pacote do ONDA está incompleto. Mantenha Onda.exe, Onda e _runtime na mesma pasta, ou reinstale o aplicativo.", "The ONDA package is incomplete. Keep Onda.exe, Onda and _runtime in the same folder, or reinstall the app.", "El paquete de ONDA está incompleto. Mantén Onda.exe, Onda y _runtime en la misma carpeta o reinstala la aplicación."), "ONDA", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return 1;
            }
            ProcessStartInfo start = new ProcessStartInfo(python);
            start.Arguments = "-s " + Quote(entry);
            foreach (string arg in args) start.Arguments += " " + Quote(arg);
            start.WorkingDirectory = root;
            start.UseShellExecute = false;
            start.CreateNoWindow = true;
            start.EnvironmentVariables["PYTHONHOME"] = Path.GetDirectoryName(python);
            start.EnvironmentVariables.Remove("PYTHONPATH");
            start.EnvironmentVariables["PYTHONNOUSERSITE"] = "1";
            start.EnvironmentVariables["PYTHONUTF8"] = "1";
            start.EnvironmentVariables["ONDA_PACKAGED_ROOT"] = root;
            using (Process process = Process.Start(start)) {
                process.WaitForExit();
                return process.ExitCode;
            }
        } catch (Exception error) {
            MessageBox.Show(T("Não foi possível abrir o ONDA.\n", "Could not open ONDA.\n", "No se pudo abrir ONDA.\n") + error.Message, "ONDA", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
}
