using System.Runtime.InteropServices;
using System.Text;
using System.Windows;
using WindowsStepGuide.Client.Contracts;

namespace WindowsStepGuide.Client.Services;

public interface IObservationContextProvider
{
    ObservationDto CreateObservation(string? sessionId);
}

public sealed class ObservationContextProvider : IObservationContextProvider
{
    private const string GuideWindowTitle = "Windows Step Guide";
    private const string FallbackForegroundWindowTitle = "unknown-foreground-window";
    private const int FallbackScreenWidth = 1280;
    private const int FallbackScreenHeight = 720;
    private const string FallbackScreenshotRef = "local://observation/fallback";
    private readonly IForegroundWindowAutomationProvider _foregroundWindowAutomationProvider;
    private ForegroundWindowObservationCache? _lastMeaningfulObservation;

    public ObservationContextProvider(IForegroundWindowAutomationProvider foregroundWindowAutomationProvider)
    {
        _foregroundWindowAutomationProvider = foregroundWindowAutomationProvider;
    }

    public ObservationDto CreateObservation(string? sessionId)
    {
        string capturedAtUtc = DateTime.UtcNow.ToString("O");
        (int screenWidth, int screenHeight) = GetScreenSize();
        string foregroundWindowTitle = GetForegroundWindowTitle();
        ForegroundWindowAutomationSnapshot automationSnapshot = _foregroundWindowAutomationProvider.Capture();
        (string effectiveTitle, ForegroundWindowAutomationSnapshot effectiveSnapshot) =
            ResolveEffectiveObservationWindow(foregroundWindowTitle, automationSnapshot);

        return new ObservationDto
        {
            SessionId = sessionId,
            CapturedAtUtc = capturedAtUtc,
            ForegroundWindowTitle = effectiveTitle,
            ForegroundWindowUiaName = effectiveSnapshot.Name,
            ForegroundWindowUiaAutomationId = effectiveSnapshot.AutomationId,
            ForegroundWindowUiaClassName = effectiveSnapshot.ClassName,
            ForegroundWindowUiaControlType = effectiveSnapshot.ControlType,
            ForegroundWindowUiaIsEnabled = effectiveSnapshot.IsEnabled,
            ForegroundWindowUiaChildCount = effectiveSnapshot.ChildCount,
            ForegroundWindowUiaChildSummary = effectiveSnapshot.ChildSummary,
            ForegroundWindowActionableSummary = BuildActionableSummary(
                effectiveTitle,
                effectiveSnapshot),
            ForegroundWindowCandidateCount = effectiveSnapshot.CandidateElements.Count,
            ForegroundWindowScanNodeCount = effectiveSnapshot.ScannedNodeCount,
            ForegroundWindowScanDepth = effectiveSnapshot.MaxDepthReached,
            ForegroundWindowCandidateElements = effectiveSnapshot.CandidateElements,
            ScreenWidth = screenWidth,
            ScreenHeight = screenHeight,
            ScreenshotRef = GenerateScreenshotRef(capturedAtUtc),
            ScreenshotStatus = "not_captured_yet",
            ScreenshotLocalPath = null,
        };
    }

    private (string Title, ForegroundWindowAutomationSnapshot Snapshot) ResolveEffectiveObservationWindow(
        string foregroundWindowTitle,
        ForegroundWindowAutomationSnapshot automationSnapshot)
    {
        if (LooksLikeGuideOrDesktopWindow(foregroundWindowTitle, automationSnapshot))
        {
            if (_lastMeaningfulObservation is not null)
            {
                return (_lastMeaningfulObservation.Title, _lastMeaningfulObservation.Snapshot);
            }
            return (foregroundWindowTitle, automationSnapshot);
        }

        _lastMeaningfulObservation = new ForegroundWindowObservationCache(
            foregroundWindowTitle,
            automationSnapshot);
        return (foregroundWindowTitle, automationSnapshot);
    }

    private static bool LooksLikeGuideOrDesktopWindow(
        string foregroundWindowTitle,
        ForegroundWindowAutomationSnapshot automationSnapshot)
    {
        if (foregroundWindowTitle.Contains(GuideWindowTitle, StringComparison.OrdinalIgnoreCase))
        {
            return true;
        }

        string className = automationSnapshot.ClassName;
        if (className.Equals("Progman", StringComparison.OrdinalIgnoreCase)
            || className.Equals("WorkerW", StringComparison.OrdinalIgnoreCase)
            || className.Equals("Shell_TrayWnd", StringComparison.OrdinalIgnoreCase))
        {
            return true;
        }

        string normalizedTitle = foregroundWindowTitle.Trim();
        string normalizedControlType = automationSnapshot.ControlType.Trim();
        return normalizedControlType.Equals("ControlType.Pane", StringComparison.OrdinalIgnoreCase)
               && (string.IsNullOrWhiteSpace(normalizedTitle)
                   || normalizedTitle.Equals("Program Manager", StringComparison.OrdinalIgnoreCase)
                   || normalizedTitle.Equals(FallbackForegroundWindowTitle, StringComparison.OrdinalIgnoreCase));
    }

    private static string BuildActionableSummary(
        string foregroundWindowTitle,
        ForegroundWindowAutomationSnapshot automationSnapshot)
    {
        string normalizedTitle = foregroundWindowTitle.Trim();
        string normalizedControlType = automationSnapshot.ControlType.Trim();
        string childSummary = string.IsNullOrWhiteSpace(automationSnapshot.ChildSummary)
            ? "unknown-children"
            : automationSnapshot.ChildSummary;

        string windowKind = "unknown";
        if (normalizedTitle.Contains("设置", StringComparison.OrdinalIgnoreCase)
            || automationSnapshot.ClassName.Contains("SystemSettings", StringComparison.OrdinalIgnoreCase)
            || automationSnapshot.AutomationId.Contains("SystemSettings", StringComparison.OrdinalIgnoreCase))
        {
            windowKind = "settings";
        }
        else if (normalizedTitle.Contains("开始", StringComparison.OrdinalIgnoreCase)
                 || automationSnapshot.ClassName.Contains("Taskbar", StringComparison.OrdinalIgnoreCase)
                 || automationSnapshot.ClassName.Contains("SearchHost", StringComparison.OrdinalIgnoreCase))
        {
            windowKind = "shell";
        }
        else if (normalizedControlType.Equals("ControlType.Window", StringComparison.OrdinalIgnoreCase)
                 || normalizedControlType.Equals("ControlType.Pane", StringComparison.OrdinalIgnoreCase))
        {
            windowKind = "window";
        }

        return
            $"window_kind={windowKind}; title={normalizedTitle}; control_type={normalizedControlType}; child_count={automationSnapshot.ChildCount}; candidate_count={automationSnapshot.CandidateElements.Count}; scanned_nodes={automationSnapshot.ScannedNodeCount}; scan_depth={automationSnapshot.MaxDepthReached}; child_summary={childSummary}";
    }

    private static string GenerateScreenshotRef(string capturedAtUtc)
    {
        try
        {
            DateTime capturedAt = DateTime.TryParse(
                capturedAtUtc,
                null,
                System.Globalization.DateTimeStyles.RoundtripKind,
                out DateTime parsedCapturedAt)
                ? parsedCapturedAt
                : DateTime.UtcNow;
            string datePart = capturedAt.ToString("yyyyMMdd");
            string timePart = capturedAt.ToString("HHmmss");
            string uniquePart = Guid.NewGuid().ToString("N")[..8];
            return $"local://observation/{datePart}/{timePart}/{uniquePart}";
        }
        catch
        {
            return FallbackScreenshotRef;
        }
    }

    private static string GetForegroundWindowTitle()
    {
        try
        {
            nint foregroundWindowHandle = GetForegroundWindow();
            if (foregroundWindowHandle == nint.Zero)
            {
                return FallbackForegroundWindowTitle;
            }

            int titleLength = GetWindowTextLength(foregroundWindowHandle);
            if (titleLength <= 0)
            {
                return FallbackForegroundWindowTitle;
            }

            StringBuilder titleBuilder = new(titleLength + 1);
            int copiedLength = GetWindowText(foregroundWindowHandle, titleBuilder, titleBuilder.Capacity);
            return copiedLength > 0
                ? titleBuilder.ToString()
                : FallbackForegroundWindowTitle;
        }
        catch
        {
            return FallbackForegroundWindowTitle;
        }
    }

    private static (int Width, int Height) GetScreenSize()
    {
        try
        {
            int width = (int)Math.Round(SystemParameters.PrimaryScreenWidth);
            int height = (int)Math.Round(SystemParameters.PrimaryScreenHeight);

            if (width <= 0 || height <= 0)
            {
                return (FallbackScreenWidth, FallbackScreenHeight);
            }

            return (width, height);
        }
        catch
        {
            return (FallbackScreenWidth, FallbackScreenHeight);
        }
    }

    [DllImport("user32.dll")]
    private static extern nint GetForegroundWindow();

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowTextLength(nint windowHandle);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowText(nint windowHandle, StringBuilder text, int maxCount);

    private sealed record ForegroundWindowObservationCache(
        string Title,
        ForegroundWindowAutomationSnapshot Snapshot);
}
