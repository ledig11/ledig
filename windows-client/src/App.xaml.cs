using System.Windows;
using WindowsStepGuide.Client.Services;

namespace WindowsStepGuide.Client
{
    public partial class App : Application
    {
        protected override void OnStartup(StartupEventArgs e)
        {
            base.OnStartup(e);

            var configWindow = new StartupConfigWindow();
            bool? configAccepted = configWindow.ShowDialog();
            if (configAccepted != true || configWindow.RuntimeModelConfig is null)
            {
                Shutdown();
                return;
            }

            RuntimeModelConfig runtimeModelConfig = configWindow.RuntimeModelConfig;
            var window = new MainWindow(runtimeModelConfig);
            window.Show();
        }
    }
}
