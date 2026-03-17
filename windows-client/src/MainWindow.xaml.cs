using System;
using System.Windows;
using WindowsStepGuide.Client.Services;
using WindowsStepGuide.Client.ViewModels;

namespace WindowsStepGuide.Client;

public partial class MainWindow : Window
{
    private readonly StepGuideViewModel _viewModel;

    public MainWindow()
    {
        InitializeComponent();

        IAnalyzeApiClient apiClient = new AnalyzeApiClient(new Uri("http://127.0.0.1:8000/"));
        _viewModel = new StepGuideViewModel(apiClient);
        DataContext = _viewModel;
    }

    private async void AnalyzeButton_Click(object sender, RoutedEventArgs e)
    {
        await _viewModel.AnalyzeAsync();
    }
}
