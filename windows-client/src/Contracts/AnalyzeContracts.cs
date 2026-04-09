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
    public string ForegroundWindowUiaName { get; set; } = string.Empty;
    public string ForegroundWindowUiaAutomationId { get; set; } = string.Empty;
    public string ForegroundWindowUiaClassName { get; set; } = string.Empty;
    public string ForegroundWindowUiaControlType { get; set; } = string.Empty;
    public bool ForegroundWindowUiaIsEnabled { get; set; }
    public int ForegroundWindowUiaChildCount { get; set; }
    public string ForegroundWindowUiaChildSummary { get; set; } = string.Empty;
    public string ForegroundWindowActionableSummary { get; set; } = string.Empty;
    public int ForegroundWindowCandidateCount { get; set; }
    public int ForegroundWindowScanNodeCount { get; set; }
    public int ForegroundWindowScanDepth { get; set; }
    public List<ObservationCandidateElementDto> ForegroundWindowCandidateElements { get; set; } = [];
    public int ScreenWidth { get; set; }
    public int ScreenHeight { get; set; }
    public string ScreenshotRef { get; set; } = string.Empty;
    public string? ScreenshotStatus { get; set; }
    public string? ScreenshotLocalPath { get; set; }
}

public sealed class ObservationCandidateElementDto
{
    public string Name { get; set; } = string.Empty;
    public string AutomationId { get; set; } = string.Empty;
    public string ClassName { get; set; } = string.Empty;
    public string ControlType { get; set; } = string.Empty;
    public bool IsEnabled { get; set; }
    public bool IsOffscreen { get; set; }
    public bool IsKeyboardFocusable { get; set; }
    public bool HasKeyboardFocus { get; set; }
    public string UiPath { get; set; } = string.Empty;
    public RectResponse BoundingRect { get; set; } = new();
}

public sealed class NextStepResponse
{
    public string SessionId { get; set; } = string.Empty;
    public string StepId { get; set; } = string.Empty;
    public string Instruction { get; set; } = string.Empty;
    public string? Message { get; set; }
    public string ActionType { get; set; } = string.Empty;
    public bool RequiresUserAction { get; set; }
    public double? Confidence { get; set; }
    public string? ObservationSummary { get; set; }
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
