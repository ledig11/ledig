using System.ComponentModel;
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
    private string _statusMessage = "等待请求后端。";
    private bool _hasHighlight;
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
        if (string.IsNullOrWhiteSpace(TaskText))
        {
            StatusMessage = "请先输入任务。";
            return;
        }

        try
        {
            NextStepResponse response = await _apiClient.AnalyzeAsync(new AnalyzeRequest
            {
                TaskText = TaskText.Trim(),
            });

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
