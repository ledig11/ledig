using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using WindowsStepGuide.Client.Contracts;

namespace WindowsStepGuide.Client.Services;

public interface IAnalyzeApiClient
{
    Task<NextStepResponse> AnalyzeAsync(AnalyzeRequest request, CancellationToken cancellationToken = default);
    Task<StepFeedbackResponse> SubmitFeedbackAsync(
        StepFeedbackRequest request,
        CancellationToken cancellationToken = default);
}

public sealed class AnalyzeApiClient : IAnalyzeApiClient
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };

    private readonly HttpClient _httpClient;

    public AnalyzeApiClient(Uri baseAddress)
    {
        _httpClient = new HttpClient
        {
            BaseAddress = baseAddress,
        };
    }

    public async Task<NextStepResponse> AnalyzeAsync(AnalyzeRequest request, CancellationToken cancellationToken = default)
    {
        using HttpResponseMessage response = await _httpClient.PostAsJsonAsync(
            "api/analyze",
            new
            {
                task_text = request.TaskText,
                observation = new
                {
                    session_id = request.Observation.SessionId,
                    captured_at_utc = request.Observation.CapturedAtUtc,
                    foreground_window_title = request.Observation.ForegroundWindowTitle,
                    screen_width = request.Observation.ScreenWidth,
                    screen_height = request.Observation.ScreenHeight,
                    screenshot_ref = request.Observation.ScreenshotRef,
                },
            },
            JsonOptions,
            cancellationToken);

        response.EnsureSuccessStatusCode();

        NextStepResponse? payload = await response.Content.ReadFromJsonAsync<NextStepResponse>(JsonOptions, cancellationToken);
        return payload ?? new NextStepResponse
        {
            Instruction = "后端返回为空。",
        };
    }

    public async Task<StepFeedbackResponse> SubmitFeedbackAsync(
        StepFeedbackRequest request,
        CancellationToken cancellationToken = default)
    {
        using HttpResponseMessage response = await _httpClient.PostAsJsonAsync(
            "api/feedback",
            new
            {
                session_id = request.SessionId,
                step_id = request.StepId,
                feedback_type = request.FeedbackType,
                comment = request.Comment,
            },
            JsonOptions,
            cancellationToken);

        response.EnsureSuccessStatusCode();

        StepFeedbackResponse? payload = await response.Content.ReadFromJsonAsync<StepFeedbackResponse>(
            JsonOptions,
            cancellationToken);

        return payload ?? new StepFeedbackResponse
        {
            Accepted = false,
            Message = "feedback response empty",
        };
    }
}
