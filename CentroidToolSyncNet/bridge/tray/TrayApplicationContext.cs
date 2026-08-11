using System.Diagnostics;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace CentroidBridge.Tray;

internal sealed class TrayApplicationContext : ApplicationContext
{
    private const int Port = 8765;
    private static readonly Uri HealthUri = new($"http://127.0.0.1:{Port}/health");

    private readonly NotifyIcon _tray;
    private readonly System.Windows.Forms.Timer _pollTimer;
    private readonly HttpClient _http = new() { Timeout = TimeSpan.FromSeconds(3) };
    private readonly Icon _icon;
    private readonly ToolStripMenuItem _mockMenuItem;
    private Process? _bridgeProcess;
    private string _lastStatusText = "Startar…";
    private bool _exiting;
    private bool _updatingMockMenu;

    public TrayApplicationContext()
    {
        var baseDir = AppContext.BaseDirectory;
        var iconPath = Path.Combine(baseDir, "bridge.ico");
        _icon = File.Exists(iconPath)
            ? new Icon(iconPath)
            : SystemIcons.Application;

        _mockMenuItem = new ToolStripMenuItem("Mock-läge")
        {
            CheckOnClick = true,
            Checked = ReadForceMock()
        };
        _mockMenuItem.CheckedChanged += (_, _) =>
        {
            if (_updatingMockMenu)
            {
                return;
            }

            ToggleMockMode(_mockMenuItem.Checked);
        };

        var menu = new ContextMenuStrip();
        menu.Opening += (_, _) => SyncMockMenuFromSettings();
        menu.Items.Add("Status", null, (_, _) => ShowStatus());
        menu.Items.Add("Öppna /health", null, (_, _) => OpenHealth());
        menu.Items.Add(new ToolStripSeparator());
        menu.Items.Add(_mockMenuItem);
        menu.Items.Add(new ToolStripSeparator());
        menu.Items.Add("Avsluta", null, (_, _) => ExitApp());

        _tray = new NotifyIcon
        {
            Icon = _icon,
            Visible = true,
            Text = "Centroid Bridge – startar…",
            ContextMenuStrip = menu
        };
        _tray.DoubleClick += (_, _) => ShowStatus();

        _pollTimer = new System.Windows.Forms.Timer { Interval = 5000 };
        _pollTimer.Tick += async (_, _) => await PollHealthAsync();
        _pollTimer.Start();

        StartBridgeProcess();
        _ = PollHealthAsync();
    }

    private static string SettingsPath =>
        Path.Combine(AppContext.BaseDirectory, "appsettings.json");

    private void SyncMockMenuFromSettings()
    {
        _updatingMockMenu = true;
        try
        {
            _mockMenuItem.Checked = ReadForceMock();
        }
        finally
        {
            _updatingMockMenu = false;
        }
    }

    private static bool ReadForceMock()
    {
        try
        {
            var path = SettingsPath;
            if (!File.Exists(path))
            {
                return false;
            }

            using var doc = JsonDocument.Parse(File.ReadAllText(path));
            if (doc.RootElement.TryGetProperty("ForceMock", out var prop))
            {
                return prop.ValueKind == JsonValueKind.True;
            }
        }
        catch
        {
            // ignore parse errors
        }

        return false;
    }

    private static void WriteForceMock(bool enabled)
    {
        var path = SettingsPath;
        JsonNode root;
        if (File.Exists(path))
        {
            root = JsonNode.Parse(File.ReadAllText(path)) ?? new JsonObject();
        }
        else
        {
            root = new JsonObject();
        }

        root["ForceMock"] = enabled;
        if (root["Port"] is null)
        {
            root["Port"] = Port;
        }

        if (root["Urls"] is null)
        {
            root["Urls"] = $"http://0.0.0.0:{Port}";
        }

        if (root["MockToolsPath"] is null)
        {
            root["MockToolsPath"] = "mock-tools.json";
        }

        var json = root.ToJsonString(new JsonSerializerOptions { WriteIndented = true });
        File.WriteAllText(path, json + Environment.NewLine, new UTF8Encoding(encoderShouldEmitUTF8Identifier: false));
    }

    private static string? ReadDllPath()
    {
        try
        {
            var path = SettingsPath;
            if (!File.Exists(path))
            {
                return null;
            }

            using var doc = JsonDocument.Parse(File.ReadAllText(path));
            if (doc.RootElement.TryGetProperty("CentroidApiDllPath", out var prop))
            {
                return prop.GetString();
            }
        }
        catch
        {
            // ignore
        }

        return null;
    }

    private void ToggleMockMode(bool enabled)
    {
        try
        {
            if (!enabled)
            {
                var dllPath = ReadDllPath();
                if (string.IsNullOrWhiteSpace(dllPath) || !File.Exists(dllPath))
                {
                    MessageBox.Show(
                        "Live-läge kräver att CentroidAPI.dll finns och att CNC12 körs.\n\n" +
                        $"Konfigurerad sökväg:\n{dllPath ?? "(saknas)"}\n\n" +
                        "Bryggan faller tillbaka till mock om live misslyckas.",
                        "Centroid Bridge – live-läge",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Warning);
                }
            }

            WriteForceMock(enabled);
            _lastStatusText = enabled
                ? "Byter till mock-läge och startar om bridge…"
                : "Byter till live-läge och startar om bridge…";
            _tray.Text = Truncate(enabled
                ? "Centroid Bridge – mock (omstart)"
                : "Centroid Bridge – live (omstart)");

            StopBridgeProcesses();
            StartBridgeProcess();
            _ = PollHealthAsync();
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                "Kunde inte växla mock-läge:\n" + ex.Message,
                "Centroid Bridge",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
            SyncMockMenuFromSettings();
        }
    }

    private void StartBridgeProcess()
    {
        var exe = Path.Combine(AppContext.BaseDirectory, "CentroidBridge.exe");
        if (!File.Exists(exe))
        {
            _lastStatusText = $"Saknar CentroidBridge.exe i:\n{AppContext.BaseDirectory}";
            _tray.Text = "Centroid Bridge – fel (exe saknas)";
            return;
        }

        StopBridgeProcesses();

        var psi = new ProcessStartInfo
        {
            FileName = exe,
            WorkingDirectory = AppContext.BaseDirectory,
            UseShellExecute = false,
            CreateNoWindow = true,
            WindowStyle = ProcessWindowStyle.Hidden
        };

        try
        {
            _bridgeProcess = Process.Start(psi);
            var mode = ReadForceMock() ? "mock" : "live";
            _lastStatusText = $"Bridge-process startad ({mode}). Väntar på /health…";
        }
        catch (Exception ex)
        {
            _lastStatusText = "Kunde inte starta CentroidBridge.exe:\n" + ex.Message;
            _tray.Text = "Centroid Bridge – startfel";
        }
    }

    private async Task PollHealthAsync()
    {
        if (_exiting)
        {
            return;
        }

        try
        {
            if (_bridgeProcess is { HasExited: true })
            {
                _lastStatusText = $"Bridge-processen avslutades (kod {_bridgeProcess.ExitCode}). Försöker starta om…";
                _tray.Text = "Centroid Bridge – omstart";
                StartBridgeProcess();
                return;
            }

            using var response = await _http.GetAsync(HealthUri);
            var body = await response.Content.ReadAsStringAsync();
            if (!response.IsSuccessStatusCode)
            {
                _lastStatusText = $"HTTP {(int)response.StatusCode}\n{body}";
                _tray.Text = "Centroid Bridge – HTTP-fel";
                return;
            }

            using var doc = JsonDocument.Parse(body);
            var root = doc.RootElement;
            var ok = root.TryGetProperty("ok", out var okProp) && okProp.GetBoolean();
            var source = root.TryGetProperty("source", out var src) ? src.GetString() : "?";
            var count = root.TryGetProperty("toolCount", out var tc) ? tc.GetInt32() : 0;
            var message = root.TryGetProperty("message", out var msg) ? msg.GetString() : "";
            var forceMock = ReadForceMock();

            _lastStatusText =
                $"ok={ok}\nsource={source}\nForceMock={forceMock}\ntoolCount={count}\nmessage={message}\n\n{HealthUri}";
            _tray.Text = Truncate($"Centroid Bridge – OK ({source}, {count} verktyg)");
        }
        catch (Exception ex)
        {
            _lastStatusText = $"Ingen kontakt med {HealthUri}\n{ex.Message}";
            _tray.Text = "Centroid Bridge – offline";
        }
    }

    private void ShowStatus()
    {
        MessageBox.Show(
            _lastStatusText,
            "Centroid Bridge – status",
            MessageBoxButtons.OK,
            MessageBoxIcon.Information);
    }

    private static void OpenHealth()
    {
        Process.Start(new ProcessStartInfo
        {
            FileName = HealthUri.ToString(),
            UseShellExecute = true
        });
    }

    private void ExitApp()
    {
        _exiting = true;
        _pollTimer.Stop();
        StopBridgeProcesses();
        _tray.Visible = false;
        _tray.Dispose();
        _icon.Dispose();
        _http.Dispose();
        ExitThread();
    }

    private void StopBridgeProcesses()
    {
        try
        {
            if (_bridgeProcess is { HasExited: false })
            {
                _bridgeProcess.Kill(entireProcessTree: true);
                _bridgeProcess.WaitForExit(3000);
            }
        }
        catch
        {
            // ignore
        }
        finally
        {
            _bridgeProcess?.Dispose();
            _bridgeProcess = null;
        }

        try
        {
            foreach (var p in Process.GetProcessesByName("CentroidBridge"))
            {
                try
                {
                    p.Kill(entireProcessTree: true);
                }
                catch
                {
                    // ignore
                }
            }
        }
        catch
        {
            // ignore
        }
    }

    private static string Truncate(string text, int max = 63)
    {
        if (string.IsNullOrEmpty(text) || text.Length <= max)
        {
            return text;
        }

        return text.Substring(0, max - 1) + "…";
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            _exiting = true;
            _pollTimer.Dispose();
            StopBridgeProcesses();
            _tray.Dispose();
            _icon.Dispose();
            _http.Dispose();
        }

        base.Dispose(disposing);
    }
}
