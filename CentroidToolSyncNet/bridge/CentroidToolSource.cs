using System.Reflection;

namespace CentroidBridge;

/// <summary>
/// Loads CentroidAPI.dll at runtime via reflection so the bridge builds without the DLL present.
/// Requires CNC12 running on the CNC PC when used live.
/// </summary>
public sealed class CentroidToolSource : IToolSource
{
    private readonly string _dllPath;

    public CentroidToolSource(string dllPath)
    {
        _dllPath = dllPath;
    }

    public string SourceName => "centroid";

    public static bool CanUse(string dllPath) => File.Exists(dllPath);

    public ToolsResponse GetTools()
    {
        if (!File.Exists(_dllPath))
        {
            throw new FileNotFoundException($"CentroidAPI.dll hittades inte: {_dllPath}");
        }

        var asm = Assembly.LoadFrom(_dllPath);
        var pipeType = asm.GetType("CentroidAPI.CNCPipe")
            ?? throw new InvalidOperationException("Typen CentroidAPI.CNCPipe saknas i DLL.");

        var pipe = Activator.CreateInstance(pipeType)
            ?? throw new InvalidOperationException("Kunde inte skapa CNCPipe.");

        // Prefer pipe.tool property if present; otherwise construct Tool(pipe)
        object toolApi;
        var toolProp = pipeType.GetProperty("tool", BindingFlags.Public | BindingFlags.Instance | BindingFlags.IgnoreCase)
            ?? pipeType.GetProperty("Tool", BindingFlags.Public | BindingFlags.Instance);
        if (toolProp != null)
        {
            toolApi = toolProp.GetValue(pipe)
                ?? throw new InvalidOperationException("CNCPipe.tool var null.");
        }
        else
        {
            var toolType = asm.GetType("CentroidAPI.CNCPipe+Tool")
                ?? asm.GetType("CentroidAPI.CNCPipe.Tool")
                ?? throw new InvalidOperationException("Typen Tool saknas i CentroidAPI.");
            toolApi = Activator.CreateInstance(toolType, pipe)
                ?? throw new InvalidOperationException("Kunde inte skapa Tool-API.");
        }

        var toolTypeRuntime = toolApi.GetType();
        var getLibrary = toolTypeRuntime.GetMethod("GetToolLibrary")
            ?? throw new InvalidOperationException("GetToolLibrary saknas.");

        object?[] args = new object?[] { null };
        var rc = getLibrary.Invoke(toolApi, args);
        EnsureSuccess(rc, "GetToolLibrary");

        if (args[0] is not System.Collections.IEnumerable library)
        {
            throw new InvalidOperationException("GetToolLibrary returnerade ingen lista.");
        }

        var tools = new List<ToolDto>();
        var skipped = 0;

        foreach (var info in library)
        {
            if (info is null)
            {
                continue;
            }

            var dto = MapInfo(info, toolApi, toolTypeRuntime);
            if (string.IsNullOrWhiteSpace(dto.description) || dto.tool_number <= 0)
            {
                skipped++;
                continue;
            }

            tools.Add(dto);
        }

        return new ToolsResponse { tools = tools, skipped_empty = skipped };
    }

    private static ToolDto MapInfo(object info, object toolApi, Type toolType)
    {
        var infoType = info.GetType();
        int toolNumber = ReadInt(info, infoType, "toolNumber", "ToolNumber", "number", "Number", "T");
        if (toolNumber <= 0)
        {
            toolNumber = ReadInt(info, infoType, "t", "Tool");
        }

        string description = ReadString(info, infoType, "description", "Description") ?? "";
        if (string.IsNullOrWhiteSpace(description) && toolNumber > 0)
        {
            description = InvokeStringOut(toolApi, toolType, "GetToolDescription", toolNumber) ?? "";
        }

        int h = ReadInt(info, infoType, "hNumber", "HNumber", "heightOffsetNumber", "H");
        int d = ReadInt(info, infoType, "dNumber", "DNumber", "diameterOffsetNumber", "D");
        double offset = ReadDouble(info, infoType, "heightOffsetAmount", "HeightOffsetAmount", "offset", "Offset");
        double diameter = ReadDouble(info, infoType, "diameterOffsetAmount", "DiameterOffsetAmount", "diameter", "Diameter");
        double speed = ReadDouble(info, infoType, "spindleSpeed", "SpindleSpeed", "speed", "Speed");
        string coolant = ReadEnumName(info, infoType, "coolant", "Coolant") ?? "OFF";
        string spindle = ReadEnumName(info, infoType, "spindleDirection", "SpindleDirection", "spindle", "Spindle") ?? "OFF";

        if (toolNumber > 0)
        {
            if (h <= 0)
            {
                h = InvokeIntOut(toolApi, toolType, "GetToolHNumber", toolNumber) ?? toolNumber;
            }
            if (d <= 0)
            {
                d = InvokeIntOut(toolApi, toolType, "GetToolDNumber", toolNumber) ?? toolNumber;
            }
            if (Math.Abs(speed) < 0.0001)
            {
                speed = InvokeIntOut(toolApi, toolType, "GetToolSpindleSpeed", toolNumber) ?? 0;
            }
            if (Math.Abs(offset) < 0.0001)
            {
                offset = InvokeDoubleOut(toolApi, toolType, "GetHeightOffsetAmount", h > 0 ? h : toolNumber) ?? 0;
            }
            if (Math.Abs(diameter) < 0.0001)
            {
                diameter = InvokeDoubleOut(toolApi, toolType, "GetDiameterOffsetAmount", d > 0 ? d : toolNumber) ?? 0;
            }
        }

        return new ToolDto
        {
            tool_number = toolNumber,
            h_number = h > 0 ? h : toolNumber,
            d_number = d > 0 ? d : toolNumber,
            offset = offset,
            diameter = diameter,
            coolant = coolant.ToUpperInvariant(),
            spindle = spindle.ToUpperInvariant(),
            speed = speed,
            description = description.Trim()
        };
    }

    private static void EnsureSuccess(object? returnCode, string op)
    {
        if (returnCode is null)
        {
            return;
        }

        var name = returnCode.ToString() ?? "";
        if (name.Contains("SUCCESS", StringComparison.OrdinalIgnoreCase) || name == "0")
        {
            return;
        }

        // Some builds use int enums
        if (returnCode is int i && i == 0)
        {
            return;
        }

        throw new InvalidOperationException($"{op} misslyckades: {name}. Är CNC12 igång?");
    }

    private static int ReadInt(object obj, Type type, params string[] names)
    {
        foreach (var name in names)
        {
            var prop = type.GetProperty(name, BindingFlags.Public | BindingFlags.Instance | BindingFlags.IgnoreCase);
            if (prop == null)
            {
                continue;
            }

            var val = prop.GetValue(obj);
            if (val is null)
            {
                continue;
            }

            try
            {
                return Convert.ToInt32(val);
            }
            catch
            {
                // continue
            }
        }

        return 0;
    }

    private static double ReadDouble(object obj, Type type, params string[] names)
    {
        foreach (var name in names)
        {
            var prop = type.GetProperty(name, BindingFlags.Public | BindingFlags.Instance | BindingFlags.IgnoreCase);
            if (prop == null)
            {
                continue;
            }

            var val = prop.GetValue(obj);
            if (val is null)
            {
                continue;
            }

            try
            {
                return Convert.ToDouble(val);
            }
            catch
            {
                // continue
            }
        }

        return 0;
    }

    private static string? ReadString(object obj, Type type, params string[] names)
    {
        foreach (var name in names)
        {
            var prop = type.GetProperty(name, BindingFlags.Public | BindingFlags.Instance | BindingFlags.IgnoreCase);
            if (prop == null)
            {
                continue;
            }

            var val = prop.GetValue(obj);
            if (val is string s)
            {
                return s;
            }
        }

        return null;
    }

    private static string? ReadEnumName(object obj, Type type, params string[] names)
    {
        foreach (var name in names)
        {
            var prop = type.GetProperty(name, BindingFlags.Public | BindingFlags.Instance | BindingFlags.IgnoreCase);
            if (prop == null)
            {
                continue;
            }

            var val = prop.GetValue(obj);
            if (val is null)
            {
                continue;
            }

            return val.ToString();
        }

        return null;
    }

    private static int? InvokeIntOut(object api, Type type, string methodName, int arg)
    {
        var method = type.GetMethods().FirstOrDefault(m =>
            m.Name == methodName && m.GetParameters().Length == 2);
        if (method is null)
        {
            return null;
        }

        object?[] args = new object?[] { arg, 0 };
        var rc = method.Invoke(api, args);
        try
        {
            EnsureSuccess(rc, methodName);
        }
        catch
        {
            return null;
        }

        try
        {
            return Convert.ToInt32(args[1]);
        }
        catch
        {
            return null;
        }
    }

    private static double? InvokeDoubleOut(object api, Type type, string methodName, int arg)
    {
        var method = type.GetMethods().FirstOrDefault(m =>
            m.Name == methodName && m.GetParameters().Length == 2);
        if (method is null)
        {
            return null;
        }

        object?[] args = new object?[] { arg, 0.0 };
        var rc = method.Invoke(api, args);
        try
        {
            EnsureSuccess(rc, methodName);
        }
        catch
        {
            return null;
        }

        try
        {
            return Convert.ToDouble(args[1]);
        }
        catch
        {
            return null;
        }
    }

    private static string? InvokeStringOut(object api, Type type, string methodName, int arg)
    {
        var method = type.GetMethods().FirstOrDefault(m =>
            m.Name == methodName && m.GetParameters().Length == 2);
        if (method is null)
        {
            return null;
        }

        object?[] args = new object?[] { arg, "" };
        var rc = method.Invoke(api, args);
        try
        {
            EnsureSuccess(rc, methodName);
        }
        catch
        {
            return null;
        }

        return args[1]?.ToString();
    }
}
