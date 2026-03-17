using System.ComponentModel;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using WindowsStepGuide.Client.Contracts;
using WindowsStepGuide.Client.Services;

namespace WindowsStepGuide.Client.ViewModels;

public sealed class StepGuideViewModel : INotifyPropertyChanged
{
    private const double PreviewCanvasWidth = 240;
    private const double PreviewCanvasHeight = 140;

    private readonly IAnalyzeApiClient _apiClient;
    private string _taskText = "打开设置";
    private string _instruction = "点击“分析下一步”开始。";
    private string _highlightText = "暂无高亮区域。";
    private string _lastFeedbackText = "暂无 feedback 提交。";
    private string _lastFeedbackType = "none";
    private string _lastObservationSummary = "暂无 observation。";
    private string _statusMessage = "等待请求后端。";
    private string _analyzeNextButtonText = "分析下一步";
    private string _reanalyzeButtonText = "重新分析";
    private bool _canAnalyze = true;
    private bool _hasHighlight;
    private string _currentSessionId = "local-session-pending";
    private string _currentStepId = "step-pending";
    private double _overlayLeft;
    private double _overlayTop;
    private double _overlayWidth;
    private double _overlayHeight;
    private double _previewLeft;
    private double _previewTop;
    private double _previewWidth;
    private double _previewHeight;

    public StepGuideViewModel(IAnalyzeApiClient apiClient)
    {
        _apiClient = apiClient;
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    public string TaskText
    {
        get => _taskText;
        set => SetField(ref _taskText, value);
    }

    public string Instruction
    {
        get => _instruction;
        private set => SetField(ref _instruction, value);
    }

    public string StatusMessage
    {
        get => _statusMessage;
        private set => SetField(ref _statusMessage, value);
    }

    public string HighlightText
    {
        get => _highlightText;
        private set => SetField(ref _highlightText, value);
    }

    public string LastFeedbackText
    {
        get => _lastFeedbackText;
        private set => SetField(ref _lastFeedbackText, value);
    }

    public string LastObservationSummary
    {
        get => _lastObservationSummary;
        private set => SetField(ref _lastObservationSummary, value);
    }

    public string CurrentSessionId => _currentSessionId;

    public string CurrentStepId => _currentStepId;

    public string LastFeedbackType
    {
        get => _lastFeedbackType;
        private set => SetField(ref _lastFeedbackType, value);
    }

    public bool CanAnalyze
    {
        get => _canAnalyze;
        private set => SetField(ref _canAnalyze, value);
    }

    public string AnalyzeNextButtonText
    {
        get => _analyzeNextButtonText;
        private set => SetField(ref _analyzeNextButtonText, value);
    }

    public string ReanalyzeButtonText
    {
        get => _reanalyzeButtonText;
        private set => SetField(ref _reanalyzeButtonText, value);
    }

    public bool HasHighlight
    {
        get => _hasHighlight;
        private set
        {
            if (SetField(ref _hasHighlight, value))
            {
                OnPropertyChanged(nameof(HasNoHighlight));
            }
        }
    }

    public bool HasNoHighlight => !HasHighlight;

    public double OverlayLeft
    {
        get => _overlayLeft;
        private set => SetField(ref _overlayLeft, value);
    }

    public double OverlayTop
    {
        get => _overlayTop;
        private set => SetField(ref _overlayTop, value);
    }

    public double OverlayWidth
    {
        get => _overlayWidth;
        private set => SetField(ref _overlayWidth, value);
    }

    public double OverlayHeight
    {
        get => _overlayHeight;
        private set => SetField(ref _overlayHeight, value);
    }

    public double PreviewCanvasDisplayWidth => PreviewCanvasWidth;

    public double PreviewCanvasDisplayHeight => PreviewCanvasHeight;

    public double PreviewLeft
    {
        get => _previewLeft;
        private set => SetField(ref _previewLeft, value);
    }

    public double PreviewTop
    {
        get => _previewTop;
        private set => SetField(ref _previewTop, value);
    }

    public double PreviewWidth
    {
        get => _previewWidth;
        private set => SetField(ref _previewWidth, value);
    }

    public double PreviewHeight
    {
        get => _previewHeight;
        private set => SetField(ref _previewHeight, value);
    }

    public async Task AnalyzeAsync()
    {
        await AnalyzeAsync(CreateObservation());
    }

    public async Task AnalyzeAsync(ObservationDto observation)
    {
        if (string.IsNullOrWhiteSpace(TaskText))
        {
            StatusMessage = "请先输入任务。";
            return;
        }

        try
        {
            CanAnalyze = false;
            AnalyzeNextButtonText = "分析中...";
            ReanalyzeButtonText = "分析中...";
            NextStepResponse response = await _apiClient.AnalyzeAsync(new AnalyzeRequest
            {
                TaskText = TaskText.Trim(),
                Observation = observation,
            });

            LastObservationSummary =
                $"foreground_window_title={observation.ForegroundWindowTitle}\nscreen={observation.ScreenWidth}x{observation.ScreenHeight}\nscreenshot_ref={observation.ScreenshotRef}";
            _currentSessionId = string.IsNullOrWhiteSpace(response.SessionId)
                ? "local-session-pending"
                : response.SessionId;
            _currentStepId = string.IsNullOrWhiteSpace(response.StepId)
                ? "step-pending"
                : response.StepId;
            OnPropertyChanged(nameof(CurrentSessionId));
            OnPropertyChanged(nameof(CurrentStepId));
            Instruction = response.Instruction;
            HighlightText = FormatHighlight(response.Highlight);
            UpdateHighlightPreview(response.Highlight);
        }
        catch (Exception ex)
        {
            HighlightText = "暂无高亮区域。";
            UpdateHighlightPreview(null);
            StatusMessage = $"请求失败: {ex.Message}";
        }
        finally
        {
            CanAnalyze = true;
            AnalyzeNextButtonText = "分析下一步";
            ReanalyzeButtonText = "重新分析";
        }
    }

    public ObservationDto CreateObservation()
    {
        return new ObservationDto
        {
            SessionId = _currentSessionId == "local-session-pending" ? null : _currentSessionId,
            CapturedAtUtc = DateTime.UtcNow.ToString("O"),
            ForegroundWindowTitle = "Windows Step Guide Panel",
            ScreenWidth = 1280,
            ScreenHeight = 720,
            ScreenshotRef = "placeholder://no-screenshot",
        };
    }

    public void MarkAnalysisStarted()
    {
        StatusMessage = "正在分析，overlay 已临时隐藏。";
    }

    public void MarkAnalysisCompleted()
    {
        StatusMessage = HasHighlight
            ? "分析完成，overlay 已更新。"
            : "分析完成，当前无高亮。";
    }

    public void MarkStepIncorrect()
    {
        StatusMessage = "已收到“这一步不对”的反馈。当前高亮已隐藏，请点击“重新分析”获取新的建议。";
    }

    public void MarkStepCompleted()
    {
        StatusMessage = "已记录“已完成”反馈。当前步骤已标记完成。";
    }

    public void MarkFeedbackSubmitted(string feedbackType)
    {
        StatusMessage = feedbackType switch
        {
            "completed" => "已提交“已完成” feedback。当前步骤已标记完成。",
            "incorrect" => "已提交“这一步不对” feedback。当前高亮已隐藏，请点击“重新分析”获取新的建议。",
            "reanalyze" => "已提交重新分析 feedback，正在获取新的建议。",
            _ => "feedback 已提交。",
        };
    }

    public void MarkFeedbackSubmissionFailed(string feedbackType)
    {
        StatusMessage = feedbackType switch
        {
            "completed" => "“已完成” feedback 提交失败。",
            "incorrect" => "“这一步不对” feedback 提交失败。当前高亮已隐藏，请点击“重新分析”获取新的建议。",
            "reanalyze" => "重新分析 feedback 提交失败，仍将继续请求新的建议。",
            _ => "feedback 提交失败。",
        };
    }

    public StepFeedbackRequest CreateFeedbackRequest(string feedbackType, string? comment = null)
    {
        StepFeedbackRequest feedback = new()
        {
            SessionId = _currentSessionId,
            StepId = _currentStepId,
            FeedbackType = feedbackType,
            Comment = comment,
        };

        Debug.WriteLine(
            $"Local StepFeedbackRequest => session_id={feedback.SessionId}, step_id={feedback.StepId}, feedback_type={feedback.FeedbackType}, comment={feedback.Comment}");

        return feedback;
    }

    public async Task<bool> SubmitFeedbackAsync(string feedbackType, string? comment = null)
    {
        StepFeedbackRequest feedback = CreateFeedbackRequest(feedbackType, comment);

        try
        {
            StepFeedbackResponse response = await _apiClient.SubmitFeedbackAsync(feedback);
            LastFeedbackType = response.FeedbackType;
            LastFeedbackText =
                $"type={response.FeedbackType}\nsession={response.SessionId}\nstep={response.StepId}\nstatus={(response.Accepted ? "accepted" : "rejected")}\nmessage={response.Message}";
            return response.Accepted;
        }
        catch (Exception ex)
        {
            LastFeedbackType = feedback.FeedbackType;
            LastFeedbackText =
                $"type={feedback.FeedbackType}\nsession={feedback.SessionId}\nstep={feedback.StepId}\nstatus=failed\nmessage={ex.Message}";
            return false;
        }
    }

    private static string FormatHighlight(HighlightResponse? highlight)
    {
        RectResponse? rect = highlight?.Rect;
        if (rect is null)
        {
            return "暂无高亮区域。";
        }

        return $"x={rect.X}, y={rect.Y}, width={rect.Width}, height={rect.Height}";
    }

    private void UpdateHighlightPreview(HighlightResponse? highlight)
    {
        RectResponse? rect = highlight?.Rect;
        if (rect is null || rect.Width <= 0 || rect.Height <= 0)
        {
            HasHighlight = false;
            OverlayLeft = 0;
            OverlayTop = 0;
            OverlayWidth = 0;
            OverlayHeight = 0;
            PreviewLeft = 0;
            PreviewTop = 0;
            PreviewWidth = 0;
            PreviewHeight = 0;
            return;
        }

        double sourceWidth = Math.Max(rect.X + rect.Width, 1);
        double sourceHeight = Math.Max(rect.Y + rect.Height, 1);
        double scale = Math.Min(PreviewCanvasWidth / sourceWidth, PreviewCanvasHeight / sourceHeight);

        HasHighlight = true;
        OverlayLeft = rect.X;
        OverlayTop = rect.Y;
        OverlayWidth = rect.Width;
        OverlayHeight = rect.Height;
        PreviewLeft = rect.X * scale;
        PreviewTop = rect.Y * scale;
        PreviewWidth = Math.Max(rect.Width * scale, 4);
        PreviewHeight = Math.Max(rect.Height * scale, 4);
    }

    private bool SetField<T>(ref T field, T value, [CallerMemberName] string? propertyName = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value))
        {
            return false;
        }

        field = value;
        OnPropertyChanged(propertyName);
        return true;
    }

    private void OnPropertyChanged([CallerMemberName] string? propertyName = null)
    {
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
    }
}
