namespace WindowsStepGuide.Client.Contracts;

public sealed class AnalyzeRequest
{
    public string TaskText { get; set; } = string.Empty;
    public ObservationDto Observation { get; set; } = new();
}

public sealed class ObservationDto
{
    public string? SessionId { get; set; }
    public string CapturedAtUtc { get; set; } = string.Empty;
    public string ForegroundWindowTitle { get; set; } = string.Empty;
    public int ScreenWidth { get; set; }
    public int ScreenHeight { get; set; }
    public string ScreenshotRef { get; set; } = string.Empty;
}

public sealed class NextStepResponse
{
    public string SessionId { get; set; } = string.Empty;
    public string StepId { get; set; } = string.Empty;
    public string Instruction { get; set; } = string.Empty;
    public string ActionType { get; set; } = string.Empty;
    public bool RequiresUserAction { get; set; }
    public HighlightResponse? Highlight { get; set; }
}

public sealed class HighlightResponse
{
    public RectResponse? Rect { get; set; }
}

public sealed class RectResponse
{
    public int X { get; set; }
    public int Y { get; set; }
    public int Width { get; set; }
    public int Height { get; set; }
}

public sealed class StepFeedbackRequest
{
    public string SessionId { get; set; } = string.Empty;
    public string StepId { get; set; } = string.Empty;
    public string FeedbackType { get; set; } = string.Empty;
    public string? Comment { get; set; }
}

public sealed class StepFeedbackResponse
{
    public bool Accepted { get; set; }
    public string SessionId { get; set; } = string.Empty;
    public string StepId { get; set; } = string.Empty;
    public string FeedbackType { get; set; } = string.Empty;
    public string Message { get; set; } = string.Empty;
}
