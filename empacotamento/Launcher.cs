using System;
using System.Runtime.InteropServices;
using System.IO;
using System.Reflection;
using System.Windows.Forms;

[assembly: AssemblyTitle("Onda")]
[assembly: AssemblyProduct("Onda")]
[assembly: AssemblyVersion("1.2.1.0")]
[assembly: AssemblyFileVersion("1.2.1.0")]
[assembly: AssemblyInformationalVersion("1.2.1")]

internal static class Launcher {
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr LoadLibraryEx(string path, IntPtr file, uint flags);
    [DllImport("kernel32.dll", CharSet = CharSet.Ansi, ExactSpelling = true)]
    private static extern IntPtr GetProcAddress(IntPtr module, string name);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    private delegate int PythonMain(int argc, IntPtr argv);

    private static int RunPython(string home, string entry, string[] args) {
        // Keep the included interpreter available to worker subprocesses.
        string python = Path.Combine(home, "pythonw.exe");
        string[] dlls = Directory.GetFiles(home, "python3*.dll");
        string library = null;
        foreach (string dll in dlls) {
            string name = Path.GetFileNameWithoutExtension(dll);
            if (name.Length > 7 && name.Substring(6).Trim('0','1','2','3','4','5','6','7','8','9').Length == 0) {
                if (library != null) throw new InvalidOperationException("Ambiguous Python runtime.");
                library = dll;
            }
        }
        if (library == null) throw new FileNotFoundException("Python runtime DLL not found.");
        // Search dependencies beside the DLL and in standard Windows directories.
        IntPtr module = LoadLibraryEx(library, IntPtr.Zero, 0x00000100 | 0x00001000);
        if (module == IntPtr.Zero) throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
        IntPtr address = GetProcAddress(module, "Py_Main");
        if (address == IntPtr.Zero) throw new EntryPointNotFoundException("Py_Main");
        PythonMain main = (PythonMain)Marshal.GetDelegateForFunctionPointer(address, typeof(PythonMain));
        string[] values = new string[args.Length + 3];
        values[0] = python; values[1] = "-s"; values[2] = entry;
        Array.Copy(args, 0, values, 3, args.Length);
        IntPtr[] strings = new IntPtr[values.Length];
        IntPtr argv = Marshal.AllocHGlobal(IntPtr.Size * values.Length);
        try {
            for (int i = 0; i < values.Length; i++) {
                strings[i] = Marshal.StringToHGlobalUni(values[i]);
                Marshal.WriteIntPtr(argv, i * IntPtr.Size, strings[i]);
            }
            return main(values.Length, argv);
        } finally {
            foreach (IntPtr value in strings) if (value != IntPtr.Zero) Marshal.FreeHGlobal(value);
            Marshal.FreeHGlobal(argv);
            // Do not unload CPython: native extensions may still reference its DLL.
        }
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
            string entry = Path.Combine(root, "Onda", "qt_desktop_ui.py");
            if (!File.Exists(python) || !File.Exists(entry)) {
                MessageBox.Show(T("O pacote do ONDA está incompleto. Mantenha Onda.exe, Onda e _runtime na mesma pasta, ou reinstale o aplicativo.", "The ONDA package is incomplete. Keep Onda.exe, Onda and _runtime in the same folder, or reinstall the app.", "El paquete de ONDA está incompleto. Mantén Onda.exe, Onda y _runtime en la misma carpeta o reinstala la aplicación."), "ONDA", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return 1;
            }
            Directory.SetCurrentDirectory(root);
            Environment.SetEnvironmentVariable("PYTHONHOME", Path.GetDirectoryName(python));
            Environment.SetEnvironmentVariable("PYTHONPATH", null);
            Environment.SetEnvironmentVariable("PYTHONNOUSERSITE", "1");
            Environment.SetEnvironmentVariable("PYTHONUTF8", "1");
            Environment.SetEnvironmentVariable("ONDA_PACKAGED_ROOT", root);
            return RunPython(Path.GetDirectoryName(python), entry, args);
        } catch (Exception error) {
            MessageBox.Show(T("Não foi possível abrir o ONDA.\n", "Could not open ONDA.\n", "No se pudo abrir ONDA.\n") + error.Message, "ONDA", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
}
