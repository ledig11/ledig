using System.Windows;
using Microsoft.Extensions.DependencyInjection;
using WindowsStepGuide.Client.Services;
using WindowsStepGuide.Client.ViewModels;

namespace WindowsStepGuide.Client
{
    public partial class App : System.Windows.Application
    {
        private ServiceProvider? _serviceProvider;

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
            _serviceProvider = BuildServiceProvider(runtimeModelConfig);
            var window = _serviceProvider.GetRequiredService<MainWindow>();
            window.Show();
        }

        protected override void OnExit(ExitEventArgs e)
        {
            _serviceProvider?.Dispose();
            _serviceProvider = null;
            base.OnExit(e);
        }

        private static ServiceProvider BuildServiceProvider(RuntimeModelConfig runtimeModelConfig)
        {
            ServiceCollection services = new();
            Uri backendBaseAddress = new("http://127.0.0.1:8000/");
            services.AddSingleton(runtimeModelConfig);
            services.AddSingleton<IAnalyzeApiClient>(
                _ => new AnalyzeApiClient(backendBaseAddress, runtimeModelConfig));
            services.AddSingleton<IRealtimeEventClient>(
                _ => new RealtimeEventClient(backendBaseAddress));
            services.AddSingleton<IObservationHistoryStore, ObservationHistoryStore>();
            services.AddSingleton<IForegroundWindowAutomationProvider, ForegroundWindowAutomationProvider>();
            services.AddSingleton<IObservationContextProvider, ObservationContextProvider>();
            services.AddSingleton<IObservationManifestStore, ObservationManifestStore>();
            services.AddSingleton<StepGuideViewModel>();
            services.AddSingleton<MainWindow>();
            return services.BuildServiceProvider();
        }
    }
}
