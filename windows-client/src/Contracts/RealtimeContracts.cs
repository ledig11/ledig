namespace WindowsStepGuide.Client.Contracts;

public sealed class RealtimeEventDto
{
    public string EventType { get; set; } = string.Empty;
    public string CreatedAtUtc { get; set; } = string.Empty;
    public string SessionId { get; set; } = string.Empty;
    public string? StepId { get; set; }
    public string? ActionType { get; set; }
    public string? FeedbackType { get; set; }
    public string? PlannerSource { get; set; }
    public string? ObservationQuality { get; set; }
    public string? ScreenshotRef { get; set; }
    public string? Note { get; set; }
}
