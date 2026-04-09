namespace WindowsStepGuide.Client.Models;

public sealed class SessionStepHistoryItem
{
    public string CreatedAt { get; set; } = string.Empty;
    public string StepId { get; set; } = string.Empty;
    public string ActionType { get; set; } = string.Empty;
    public string Message { get; set; } = string.Empty;
    public string? FeedbackType { get; set; }
}

public sealed class SessionState
{
    public string SessionId { get; set; } = string.Empty;
    public string CreatedAt { get; set; } = string.Empty;
    public string? LastObservationRef { get; set; }
    public string? CurrentStepId { get; set; }
    public string? LastFeedbackType { get; set; }
    public List<SessionStepHistoryItem> StepHistory { get; set; } = [];
}

