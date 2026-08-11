namespace CentroidBridge;

public sealed class BridgeSettings
{
    public int Port { get; set; } = 8765;
    public string CentroidApiDllPath { get; set; } = @"C:\cncm\CentroidAPI.dll";
    public string MockToolsPath { get; set; } = "mock-tools.json";
    public bool ForceMock { get; set; }
}

public sealed class ToolDto
{
    public int tool_number { get; set; }
    public int h_number { get; set; }
    public int d_number { get; set; }
    public double offset { get; set; }
    public double diameter { get; set; }
    public string coolant { get; set; } = "OFF";
    public string spindle { get; set; } = "OFF";
    public double speed { get; set; }
    public string description { get; set; } = "";
}

public sealed class ToolsResponse
{
    public List<ToolDto> tools { get; set; } = new();
    public int skipped_empty { get; set; }
}

public sealed class HealthResponse
{
    public bool ok { get; set; }
    public string source { get; set; } = "mock";
    public int toolCount { get; set; }
    public string? message { get; set; }
}

public interface IToolSource
{
    string SourceName { get; }
    ToolsResponse GetTools();
}
