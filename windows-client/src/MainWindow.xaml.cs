using System;
using System.Windows;
using WindowsStepGuide.Client.Services;
using WindowsStepGuide.Client.ViewModels;

namespace WindowsStepGuide.Client;

public partial class MainWindow : Window
{
    private readonly StepGuideViewModel _viewModel;
    private readonly OverlayWindow _overlayWindow;

    public MainWindow()
    {
        InitializeComponent();

        IAnalyzeApiClient apiClient = new AnalyzeApiClient(new Uri("http://127.0.0.1:8000/"));
        _viewModel = new StepGuideViewModel(apiClient);
        _overlayWindow = new OverlayWindow();
        DataContext = _viewModel;
    }

    private async void AnalyzeButton_Click(object sender, RoutedEventArgs e)
    {
        _overlayWindow.HideHighlight();
        _viewModel.MarkAnalysisStarted();
        await _viewModel.AnalyzeAsync();

        if (_viewModel.HasHighlight)
        {
            _overlayWindow.ShowHighlight(
                _viewModel.OverlayLeft,
                _viewModel.OverlayTop,
                _viewModel.OverlayWidth,
                _viewModel.OverlayHeight);
            _viewModel.MarkAnalysisCompleted();
            return;
        }

        _overlayWindow.HideHighlight();
        _viewModel.MarkAnalysisCompleted();
    }

    protected override void OnClosed(EventArgs e)
    {
        _overlayWindow.Close();

        base.OnClosed(e);
    }
}
