namespace WindowsStepGuide.Client.Models;

public sealed class FeedbackRequest
{
    public string SessionId { get; set; } = string.Empty;
    public string StepId { get; set; } = string.Empty;
    public string FeedbackType { get; set; } = string.Empty;
    public string? Comment { get; set; }
}

public sealed class FeedbackResponse
{
    public bool Accepted { get; set; }
    public string SessionId { get; set; } = string.Empty;
    public string StepId { get; set; } = string.Empty;
    public string FeedbackType { get; set; } = string.Empty;
    public string Message { get; set; } = string.Empty;
}
