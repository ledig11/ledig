using System.Net.Http;
using System.Net.Http.Json;
using System.Linq;
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
    private readonly RuntimeModelConfig _runtimeModelConfig;

    public AnalyzeApiClient(Uri baseAddress, RuntimeModelConfig runtimeModelConfig)
    {
        _httpClient = new HttpClient
        {
            BaseAddress = baseAddress,
        };
        _runtimeModelConfig = runtimeModelConfig;
    }

    public async Task<NextStepResponse> AnalyzeAsync(AnalyzeRequest request, CancellationToken cancellationToken = default)
    {
        using HttpRequestMessage httpRequest = new(HttpMethod.Post, "api/analyze")
        {
            Content = JsonContent.Create(
                new
                {
                    task_text = request.TaskText,
                    observation = new
                    {
                        session_id = request.Observation.SessionId,
                        captured_at_utc = request.Observation.CapturedAtUtc,
                        foreground_window_title = request.Observation.ForegroundWindowTitle,
                        foreground_window_uia_name = request.Observation.ForegroundWindowUiaName,
                        foreground_window_uia_automation_id = request.Observation.ForegroundWindowUiaAutomationId,
                        foreground_window_uia_class_name = request.Observation.ForegroundWindowUiaClassName,
                        foreground_window_uia_control_type = request.Observation.ForegroundWindowUiaControlType,
                        foreground_window_uia_is_enabled = request.Observation.ForegroundWindowUiaIsEnabled,
                        foreground_window_uia_child_count = request.Observation.ForegroundWindowUiaChildCount,
                        foreground_window_uia_child_summary = request.Observation.ForegroundWindowUiaChildSummary,
                        foreground_window_actionable_summary = request.Observation.ForegroundWindowActionableSummary,
                        foreground_window_candidate_count = request.Observation.ForegroundWindowCandidateCount,
                        foreground_window_scan_node_count = request.Observation.ForegroundWindowScanNodeCount,
                        foreground_window_scan_depth = request.Observation.ForegroundWindowScanDepth,
                        foreground_window_candidate_elements = request.Observation.ForegroundWindowCandidateElements.Select(
                            candidate => new
                            {
                                name = candidate.Name,
                                automation_id = candidate.AutomationId,
                                class_name = candidate.ClassName,
                                control_type = candidate.ControlType,
                                is_enabled = candidate.IsEnabled,
                                is_offscreen = candidate.IsOffscreen,
                                is_keyboard_focusable = candidate.IsKeyboardFocusable,
                                has_keyboard_focus = candidate.HasKeyboardFocus,
                                ui_path = candidate.UiPath,
                                bounding_rect = new
                                {
                                    x = candidate.BoundingRect.X,
                                    y = candidate.BoundingRect.Y,
                                    width = candidate.BoundingRect.Width,
                                    height = candidate.BoundingRect.Height,
                                },
                            }),
                        screen_width = request.Observation.ScreenWidth,
                        screen_height = request.Observation.ScreenHeight,
                        screenshot_ref = request.Observation.ScreenshotRef,
                        screenshot_status = request.Observation.ScreenshotStatus,
                        screenshot_local_path = request.Observation.ScreenshotLocalPath,
                    },
                },
                options: JsonOptions),
        };
        httpRequest.Headers.Add("X-Model-Type", _runtimeModelConfig.ModelType);
        httpRequest.Headers.Add("X-API-Key", _runtimeModelConfig.ApiKey);

        using HttpResponseMessage response = await _httpClient.SendAsync(httpRequest, cancellationToken);

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
