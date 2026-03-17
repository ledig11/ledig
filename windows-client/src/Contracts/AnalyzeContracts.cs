namespace WindowsStepGuide.Client.Contracts;

public sealed class AnalyzeRequest
{
    public string TaskText { get; set; } = string.Empty;
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
