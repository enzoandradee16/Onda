using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Xml;

internal static class InstallerText {
    internal static readonly string[] Languages = { "pt-BR", "es", "en" };
    internal static volatile string Language = "pt-BR";
    private static readonly Dictionary<string, Dictionary<string, string>> Catalog = Load();

    private static Dictionary<string, Dictionary<string, string>> Load() {
        XmlDocument document = new XmlDocument(); document.XmlResolver = null;
        using (Stream source = Assembly.GetExecutingAssembly().GetManifestResourceStream("Onda.InstallerStrings")) document.Load(source);
        Dictionary<string, Dictionary<string, string>> result = new Dictionary<string, Dictionary<string, string>>();
        foreach (XmlElement row in document.DocumentElement.SelectNodes("text")) {
            string key = row.GetAttribute("key");
            Dictionary<string, string> values = new Dictionary<string, string>();
            foreach (string language in Languages) {
                XmlElement cell = row.SelectSingleNode("value[@lang='"+language+"']") as XmlElement;
                if (cell == null || String.IsNullOrWhiteSpace(cell.InnerText)) throw new InvalidDataException("Missing installer translation: "+key+"/"+language);
                values.Add(language, cell.InnerText);
            }
            result.Add(key, values);
        }
        return result;
    }
    internal static string T(string key, params object[] values) {
        return String.Format(CultureInfo.InvariantCulture, Catalog[key][Language], values);
    }
    internal static string Normalize(string value) {
        switch (value.ToLowerInvariant()) {
            case "pt-br": case "brazilianportuguese": return "pt-BR";
            case "es": case "spanish": return "es";
            case "en": case "english": return "en";
            default: throw new ArgumentException("Unsupported installer language: "+value);
        }
    }
    internal static string BackendLanguage {
        get { return Language == "en" ? "english" : Language == "es" ? "spanish" : "brazilianportuguese"; }
    }
    internal static string[] SelectFromArguments(string[] args) {
        List<string> remaining = new List<string>();
        foreach (string value in args) {
            if (value.StartsWith("/LANG=", StringComparison.OrdinalIgnoreCase)) Language = Normalize(value.Substring(6));
            else remaining.Add(value);
        }
        return remaining.ToArray();
    }
    internal static string[] BackendArguments(string[] args) {
        List<string> normalized = new List<string>();
        foreach (string value in args) normalized.Add(value.StartsWith("/LANG=", StringComparison.OrdinalIgnoreCase)
            ? "/LANG="+BackendLanguage : value);
        return normalized.ToArray();
    }
    internal static int Validate() {
        foreach (string key in Catalog.Keys) {
            foreach (string language in Languages) {
                string sample = Catalog[key][language];
                // Validate placeholder syntax in every language, including inactive messages.
                String.Format(CultureInfo.InvariantCulture, sample, "1", "2");
                for (int index = 0; index < 2; index++) {
                    string token = "{"+index+"}";
                    if (sample.Contains(token) != Catalog[key]["pt-BR"].Contains(token)) throw new InvalidDataException("Translation placeholder mismatch: "+key);
                }
            }
        }
        return Catalog.Count;
    }
}
