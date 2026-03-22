using System;
using System.Windows;
using WindowsStepGuide.Client.Services;
using WindowsStepGuide.Client.ViewModels;

namespace WindowsStepGuide.Client;

public partial class MainWindow : Window
{
    private readonly StepGuideViewModel _viewModel;
    private readonly OverlayWindow _overlayWindow;
    private readonly IRealtimeEventClient _realtimeEventClient;
    private CancellationTokenSource? _realtimeCts;

    public MainWindow(StepGuideViewModel viewModel, IRealtimeEventClient realtimeEventClient)
    {
        InitializeComponent();
        _viewModel = viewModel;
        _overlayWindow = new OverlayWindow();
        _realtimeEventClient = realtimeEventClient;
        DataContext = _viewModel;
        Loaded += MainWindow_Loaded;
    }

    private async void AnalyzeButton_Click(object sender, RoutedEventArgs e)
    {
        await RunAnalyzeAsync();
    }

    private async void ReanalyzeButton_Click(object sender, RoutedEventArgs e)
    {
        bool feedbackAccepted = await _viewModel.SubmitFeedbackAsync("reanalyze", "用户手动触发重新分析。");
        if (feedbackAccepted)
        {
            _viewModel.MarkFeedbackSubmitted("reanalyze");
        }
        else
        {
            _viewModel.MarkFeedbackSubmissionFailed("reanalyze");
        }

        await RunAnalyzeAsync();
    }

    private async void IncorrectStepButton_Click(object sender, RoutedEventArgs e)
    {
        _overlayWindow.HideHighlight();
        bool feedbackAccepted = await _viewModel.SubmitFeedbackAsync("incorrect", "用户认为当前建议不正确。");
        if (feedbackAccepted)
        {
            _viewModel.MarkFeedbackSubmitted("incorrect");
        }
        else
        {
            _viewModel.MarkFeedbackSubmissionFailed("incorrect");
        }

        ReanalyzeButton.Focus();
    }

    private async void CompletedStepButton_Click(object sender, RoutedEventArgs e)
    {
        bool feedbackAccepted = await _viewModel.SubmitFeedbackAsync("completed", "用户标记当前步骤已完成。");
        if (feedbackAccepted)
        {
            _viewModel.MarkFeedbackSubmitted("completed");
        }
        else
        {
            _viewModel.MarkFeedbackSubmissionFailed("completed");
        }
    }

    private async Task RunAnalyzeAsync()
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
        _realtimeCts?.Cancel();
        _realtimeCts?.Dispose();
        _realtimeCts = null;
        _overlayWindow.Close();

        base.OnClosed(e);
    }

    private void MainWindow_Loaded(object sender, RoutedEventArgs e)
    {
        _realtimeCts = new CancellationTokenSource();
        _ = _realtimeEventClient.RunAsync(
            onEvent: eventPayload => Dispatcher.Invoke(() => _viewModel.MarkRealtimeEventReceived(eventPayload)),
            onConnected: () => Dispatcher.Invoke(_viewModel.MarkRealtimeConnected),
            onDisconnected: reason => Dispatcher.Invoke(() => _viewModel.MarkRealtimeDisconnected(reason)),
            cancellationToken: _realtimeCts.Token);
    }
}
