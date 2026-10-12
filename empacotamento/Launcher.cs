using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Windows.Forms;

[assembly: AssemblyTitle("Onda")]
[assembly: AssemblyProduct("Onda")]
[assembly: AssemblyVersion("1.0.0.0")]

internal static class Launcher {
    private static string Quote(string value) {
        return "\"" + value.Replace("\"", "\\\"") + "\"";
    }
    [STAThread]
    private static int Main(string[] args) {
        try {
            string root = AppDomain.CurrentDomain.BaseDirectory;
            string python = Path.Combine(root, "_runtime", "python", "pythonw.exe");
            string entry = Path.Combine(root, "Onda", "desktop_entry.py");
            if (!File.Exists(python) || !File.Exists(entry)) {
                MessageBox.Show("O pacote do Onda esta incompleto. Mantenha Onda.exe, Onda e _runtime na mesma pasta, ou reinstale o aplicativo.", "Onda", MessageBoxButtons.OK, MessageBoxIcon.Error);
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
            MessageBox.Show("Nao foi possivel abrir o Onda.\n" + error.Message, "Onda", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
}
