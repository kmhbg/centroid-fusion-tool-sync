using System.Text.Json;

namespace CentroidBridge;

public sealed class MockToolSource : IToolSource
{
    private readonly string _path;

    public MockToolSource(string path)
    {
        _path = path;
    }

    public string SourceName => "mock";

    public ToolsResponse GetTools()
    {
        if (!File.Exists(_path))
        {
            throw new FileNotFoundException($"Mock-fil saknas: {_path}");
        }

        var json = File.ReadAllText(_path);
        var payload = JsonSerializer.Deserialize<ToolsResponse>(json, new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true
        }) ?? new ToolsResponse();

        var filtered = payload.tools
            .Where(t => !string.IsNullOrWhiteSpace(t.description) && t.tool_number > 0)
            .ToList();

        return new ToolsResponse
        {
            tools = filtered,
            skipped_empty = payload.skipped_empty
        };
    }
}
