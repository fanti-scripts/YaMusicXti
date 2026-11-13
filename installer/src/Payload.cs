using System;
using System.IO;
using System.Reflection;
using System.Text;

namespace YMBG
{
    /// <summary>
    /// Встроенный ресурс payload.bin: JS-движок, якоря и файлы по умолчанию.
    /// Генерируется tools/export_payload.py на этапе сборки.
    /// </summary>
    internal static class Payload
    {
        public static readonly string Marker;
        public static readonly string MarkerVersion;
        public static readonly string InjectFunc;
        public static readonly string Engine;
        public static readonly string AnchorFunc;
        public static readonly string AnchorHandler;
        public static readonly string AnchorInsert;
        public static readonly string Css;
        public static readonly string DefaultJson;

        static Payload()
        {
            using (Stream s = Assembly.GetExecutingAssembly().GetManifestResourceStream("payload.bin"))
            {
                if (s == null)
                {
                    throw new InvalidOperationException("payload.bin не встроен в сборку");
                }
                using (BinaryReader r = new BinaryReader(s, Encoding.UTF8))
                {
                    Marker = Read(r);
                    MarkerVersion = Read(r);
                    InjectFunc = Read(r);
                    Engine = Read(r);
                    AnchorFunc = Read(r);
                    AnchorHandler = Read(r);
                    AnchorInsert = Read(r);
                    Css = Read(r);
                    DefaultJson = Read(r);
                }
            }
        }

        private static string Read(BinaryReader r)
        {
            int len = r.ReadInt32();
            if (len < 0 || len > 64 * 1024 * 1024)
            {
                throw new InvalidDataException("повреждён payload.bin");
            }
            byte[] buf = r.ReadBytes(len);
            if (buf.Length != len)
            {
                throw new InvalidDataException("payload.bin обрезан");
            }
            return Encoding.UTF8.GetString(buf);
        }
    }
}
