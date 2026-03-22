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
    private const string FallbackForegroundWindowTitle = "unknown-foreground-window";
    private const int FallbackScreenWidth = 1280;
    private const int FallbackScreenHeight = 720;
    private const string FallbackScreenshotRef = "local://observation/fallback";
    private readonly IForegroundWindowAutomationProvider _foregroundWindowAutomationProvider;

    public ObservationContextProvider(IForegroundWindowAutomationProvider foregroundWindowAutomationProvider)
    {
        _foregroundWindowAutomationProvider = foregroundWindowAutomationProvider;
    }

    public ObservationDto CreateObservation(string? sessionId)
    {
        string capturedAtUtc = DateTime.UtcNow.ToString("O");
        (int screenWidth, int screenHeight) = GetScreenSize();
        ForegroundWindowAutomationSnapshot automationSnapshot = _foregroundWindowAutomationProvider.Capture();

        return new ObservationDto
        {
            SessionId = sessionId,
            CapturedAtUtc = capturedAtUtc,
            ForegroundWindowTitle = GetForegroundWindowTitle(),
            ForegroundWindowUiaName = automationSnapshot.Name,
            ForegroundWindowUiaAutomationId = automationSnapshot.AutomationId,
            ForegroundWindowUiaClassName = automationSnapshot.ClassName,
            ForegroundWindowUiaControlType = automationSnapshot.ControlType,
            ForegroundWindowUiaIsEnabled = automationSnapshot.IsEnabled,
            ForegroundWindowUiaChildCount = automationSnapshot.ChildCount,
            ForegroundWindowUiaChildSummary = automationSnapshot.ChildSummary,
            ForegroundWindowActionableSummary = BuildActionableSummary(
                GetForegroundWindowTitle(),
                automationSnapshot),
            ForegroundWindowCandidateElements = automationSnapshot.CandidateElements,
            ScreenWidth = screenWidth,
            ScreenHeight = screenHeight,
            ScreenshotRef = GenerateScreenshotRef(capturedAtUtc),
        };
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
            $"window_kind={windowKind}; title={normalizedTitle}; control_type={normalizedControlType}; child_count={automationSnapshot.ChildCount}; candidate_count={automationSnapshot.CandidateElements.Count}; child_summary={childSummary}";
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
}
