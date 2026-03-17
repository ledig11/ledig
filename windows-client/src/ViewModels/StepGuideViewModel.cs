using System.ComponentModel;
using System.Runtime.CompilerServices;
using WindowsStepGuide.Client.Contracts;
using WindowsStepGuide.Client.Services;

namespace WindowsStepGuide.Client.ViewModels;

public sealed class StepGuideViewModel : INotifyPropertyChanged
{
    private readonly IAnalyzeApiClient _apiClient;
    private string _taskText = "打开设置";
    private string _instruction = "点击“分析下一步”开始。";
    private string _highlightText = "暂无高亮区域。";
    private string _statusMessage = "等待请求后端。";

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

    public async Task AnalyzeAsync()
    {
        if (string.IsNullOrWhiteSpace(TaskText))
        {
            StatusMessage = "请先输入任务。";
            return;
        }

        try
        {
            StatusMessage = "正在请求后端...";
            NextStepResponse response = await _apiClient.AnalyzeAsync(new AnalyzeRequest
            {
                TaskText = TaskText.Trim(),
            });

            Instruction = response.Instruction;
            HighlightText = FormatHighlight(response.Highlight);
            StatusMessage = $"已收到 {response.StepId}";
        }
        catch (Exception ex)
        {
            StatusMessage = $"请求失败: {ex.Message}";
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

    private void SetField<T>(ref T field, T value, [CallerMemberName] string? propertyName = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value))
        {
            return;
        }

        field = value;
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
    }
}
