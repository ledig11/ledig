using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using WindowsStepGuide.Client.Contracts;
using WindowsStepGuide.Client.Models;

namespace WindowsStepGuide.Client.Services;

public interface ISessionApiClient
{
    Task<string> CreateSessionAsync(string? taskText = null, CancellationToken cancellationToken = default);
    Task<SessionState> GetSessionAsync(string sessionId, CancellationToken cancellationToken = default);
    Task<NextStepResponse> NextStepAsync(
        string sessionId,
        AnalyzeRequest request,
        CancellationToken cancellationToken = default);
    Task<FeedbackResponse> SubmitFeedbackAsync(
        string sessionId,
        FeedbackRequest request,
        CancellationToken cancellationToken = default);
}

public sealed class SessionApiClient : ISessionApiClient
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };

    private readonly HttpClient _httpClient;

    public SessionApiClient(Uri baseAddress)
    {
        _httpClient = new HttpClient
        {
            BaseAddress = baseAddress,
        };
    }

    public async Task<string> CreateSessionAsync(string? taskText = null, CancellationToken cancellationToken = default)
    {
        using HttpResponseMessage response = await _httpClient.PostAsJsonAsync(
            "api/sessions",
            new
            {
                task_text = string.IsNullOrWhiteSpace(taskText) ? null : taskText,
            },
            JsonOptions,
            cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            string errorBody = await response.Content.ReadAsStringAsync(cancellationToken);
            throw new HttpRequestException(
                $"create session failed: {(int)response.StatusCode} {response.ReasonPhrase}; body={errorBody}");
        }

        CreateSessionResponse? payload = await response.Content.ReadFromJsonAsync<CreateSessionResponse>(
            JsonOptions,
            cancellationToken);
        return payload?.SessionId ?? string.Empty;
    }

    public async Task<SessionState> GetSessionAsync(string sessionId, CancellationToken cancellationToken = default)
    {
        using HttpResponseMessage response = await _httpClient.GetAsync($"api/sessions/{sessionId}", cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            string errorBody = await response.Content.ReadAsStringAsync(cancellationToken);
            throw new HttpRequestException(
                $"get session failed: {(int)response.StatusCode} {response.ReasonPhrase}; body={errorBody}");
        }

        SessionState? payload = await response.Content.ReadFromJsonAsync<SessionState>(JsonOptions, cancellationToken);
        return payload ?? new SessionState();
    }

    public async Task<NextStepResponse> NextStepAsync(
        string sessionId,
        AnalyzeRequest request,
        CancellationToken cancellationToken = default)
    {
        using HttpResponseMessage response = await _httpClient.PostAsJsonAsync(
            $"api/sessions/{sessionId}/next-step",
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
            JsonOptions,
            cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            string errorBody = await response.Content.ReadAsStringAsync(cancellationToken);
            throw new HttpRequestException(
                $"next-step failed: {(int)response.StatusCode} {response.ReasonPhrase}; body={errorBody}");
        }

        SessionNextStepResponse? payload = await response.Content.ReadFromJsonAsync<SessionNextStepResponse>(
            JsonOptions,
            cancellationToken);
        return payload?.ToLegacyResponse() ?? new NextStepResponse
        {
            Instruction = "后端返回为空。",
        };
    }

    public async Task<FeedbackResponse> SubmitFeedbackAsync(
        string sessionId,
        FeedbackRequest request,
        CancellationToken cancellationToken = default)
    {
        using HttpResponseMessage response = await _httpClient.PostAsJsonAsync(
            $"api/sessions/{sessionId}/feedback",
            new
            {
                session_id = request.SessionId,
                step_id = request.StepId,
                feedback_type = request.FeedbackType,
                comment = request.Comment,
            },
            JsonOptions,
            cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            string errorBody = await response.Content.ReadAsStringAsync(cancellationToken);
            throw new HttpRequestException(
                $"session feedback failed: {(int)response.StatusCode} {response.ReasonPhrase}; body={errorBody}");
        }

        FeedbackResponse? payload = await response.Content.ReadFromJsonAsync<FeedbackResponse>(
            JsonOptions,
            cancellationToken);
        return payload ?? new FeedbackResponse
        {
            Accepted = false,
            Message = "feedback response empty",
        };
    }

    private sealed class CreateSessionResponse
    {
        public string SessionId { get; set; } = string.Empty;
    }

    private sealed class SessionNextStepResponse
    {
        public string SessionId { get; set; } = string.Empty;
        public string StepId { get; set; } = string.Empty;
        public string Instruction { get; set; } = string.Empty;
        public string Message { get; set; } = string.Empty;
        public string ActionType { get; set; } = string.Empty;
        public bool RequiresUserAction { get; set; }
        public HighlightResponse? Highlight { get; set; }

        public NextStepResponse ToLegacyResponse()
        {
            string instructionText = string.IsNullOrWhiteSpace(Instruction) ? Message : Instruction;
            return new NextStepResponse
            {
                SessionId = SessionId,
                StepId = StepId,
                Instruction = instructionText,
                ActionType = ActionType,
                RequiresUserAction = RequiresUserAction,
                Highlight = Highlight,
            };
        }
    }
}
