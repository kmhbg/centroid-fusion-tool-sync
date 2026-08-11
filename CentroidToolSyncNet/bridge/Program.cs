using CentroidBridge;

var builder = WebApplication.CreateBuilder(args);

var settings = new BridgeSettings();
builder.Configuration.Bind(settings);

// Allow overriding port via appsettings Urls / Port
if (settings.Port > 0)
{
    builder.WebHost.UseUrls($"http://0.0.0.0:{settings.Port}");
}

var app = builder.Build();

var contentRoot = app.Environment.ContentRootPath;
var mockPath = Path.IsPathRooted(settings.MockToolsPath)
    ? settings.MockToolsPath
    : Path.Combine(contentRoot, settings.MockToolsPath);

IToolSource ResolveSource()
{
    if (!settings.ForceMock && CentroidToolSource.CanUse(settings.CentroidApiDllPath))
    {
        try
        {
            // Probe by constructing; actual CNC12 call happens on GetTools
            return new CentroidToolSource(settings.CentroidApiDllPath);
        }
        catch
        {
            // fall through to mock
        }
    }

    return new MockToolSource(mockPath);
}

string ActiveSourceName()
{
    if (!settings.ForceMock && CentroidToolSource.CanUse(settings.CentroidApiDllPath))
    {
        return "centroid";
    }

    return "mock";
}

app.MapGet("/health", () =>
{
    try
    {
        var source = ResolveSource();
        var tools = source.GetTools();
        return Results.Json(new HealthResponse
        {
            ok = true,
            source = source.SourceName,
            toolCount = tools.tools.Count,
            message = source.SourceName == "mock"
                ? "Kör i mock-läge (CentroidAPI.dll saknas eller ForceMock=true)."
                : "Ansluten till CentroidAPI."
        });
    }
    catch (Exception ex)
    {
        // If centroid fails at runtime, fall back to mock for health if possible
        try
        {
            var mock = new MockToolSource(mockPath);
            var tools = mock.GetTools();
            return Results.Json(new HealthResponse
            {
                ok = true,
                source = "mock",
                toolCount = tools.tools.Count,
                message = $"Centroid misslyckades ({ex.Message}); använder mock."
            });
        }
        catch (Exception mockEx)
        {
            return Results.Json(new HealthResponse
            {
                ok = false,
                source = ActiveSourceName(),
                toolCount = 0,
                message = mockEx.Message
            }, statusCode: 503);
        }
    }
});

app.MapGet("/tools", () =>
{
    try
    {
        IToolSource source = ResolveSource();
        ToolsResponse response;
        try
        {
            response = source.GetTools();
        }
        catch (Exception) when (source.SourceName == "centroid")
        {
            source = new MockToolSource(mockPath);
            response = source.GetTools();
        }

        return Results.Json(response);
    }
    catch (Exception ex)
    {
        return Results.Json(new { error = ex.Message }, statusCode: 500);
    }
});

Console.WriteLine($"CentroidBridge lyssnar på http://0.0.0.0:{settings.Port}");
Console.WriteLine($"Källa: {(CentroidToolSource.CanUse(settings.CentroidApiDllPath) && !settings.ForceMock ? "centroid (om CNC12 kör)" : "mock")}");
Console.WriteLine("Endpoints: GET /health  GET /tools");

app.Run();
