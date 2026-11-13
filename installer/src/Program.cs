using System;
using System.Threading;
using System.Windows.Forms;

[assembly: System.Reflection.AssemblyTitle("Фон Яндекс Музыки — установщик")]
[assembly: System.Reflection.AssemblyDescription("Установщик мода «Фон Яндекс Музыки»")]
[assembly: System.Reflection.AssemblyProduct("Фон Яндекс Музыки")]
[assembly: System.Reflection.AssemblyCopyright("Неофициальный мод")]
[assembly: System.Reflection.AssemblyVersion("2.0.0.0")]
[assembly: System.Reflection.AssemblyFileVersion("2.0.0.0")]
[assembly: System.Runtime.InteropServices.ComVisible(false)]

namespace YMBG
{
    internal static class Program
    {
        [STAThread]
        private static int Main(string[] args)
        {
            if (args != null && args.Length > 0)
            {
                return Cli.Run(args);
            }

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            bool created;
            using (Mutex mutex = new Mutex(true, @"Local\YMBgInstaller", out created))
            {
                if (!created)
                {
                    return 0;
                }
                Application.Run(new MainForm(null));
                GC.KeepAlive(mutex);
            }
            return 0;
        }
    }
}
