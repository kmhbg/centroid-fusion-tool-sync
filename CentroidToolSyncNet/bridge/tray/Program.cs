namespace CentroidBridge.Tray;

internal static class Program
{
    private const string MutexName = @"Local\CentroidBridgeTraySingleton";

    [STAThread]
    private static void Main()
    {
        using var mutex = new Mutex(true, MutexName, out var createdNew);
        if (!createdNew)
        {
            MessageBox.Show(
                "Centroid Bridge körs redan (systemfacksikon).",
                "Centroid Bridge",
                MessageBoxButtons.OK,
                MessageBoxIcon.Information);
            return;
        }

        ApplicationConfiguration.Initialize();
        Application.Run(new TrayApplicationContext());
    }
}
