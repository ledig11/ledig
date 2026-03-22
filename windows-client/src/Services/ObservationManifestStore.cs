using System.Globalization;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Text.Json;
using System.Windows.Forms;
using WindowsStepGuide.Client.Contracts;

namespace WindowsStepGuide.Client.Services;

public interface IObservationManifestStore
{
    ObservationManifestSaveResult Save(ObservationDto observation);
}

public sealed class ObservationManifestStore : IObservationManifestStore
{
    private const string ProductFolderName = "WindowsStepGuide";
    private const string ObservationFolderName = "observations";
    private const string ManifestFolderName = "manifests";
    private const string ScreenshotFolderName = "screenshots";
    private const string FallbackDateFolder = "unknown-date";
    private static readonly JsonSerializerOptions SerializerOptions = new()
    {
        WriteIndented = true,
    };

    public ObservationManifestSaveResult Save(ObservationDto observation)
    {
        try
        {
            string manifestDirectoryPath = GetManifestDirectoryPath(observation.CapturedAtUtc);
            Directory.CreateDirectory(manifestDirectoryPath);
            string? screenshotLocalPath = TryCaptureScreenshot(observation);

            string manifestFilePath = Path.Combine(
                manifestDirectoryPath,
                $"{SanitizeFileName(observation.ScreenshotRef)}.json");

            ObservationManifestRecord manifest = new()
            {
                SavedAtUtc = DateTime.UtcNow.ToString("O"),
                SessionId = observation.SessionId,
                CapturedAtUtc = observation.CapturedAtUtc,
                ForegroundWindowTitle = observation.ForegroundWindowTitle,
                ScreenWidth = observation.ScreenWidth,
                ScreenHeight = observation.ScreenHeight,
                ScreenshotRef = observation.ScreenshotRef,
                ScreenshotStatus = screenshotLocalPath is null ? "capture-failed" : "captured",
                ScreenshotLocalPath = screenshotLocalPath,
                ForegroundWindowAutomation = new ObservationAutomationRecord
                {
                    Name = observation.ForegroundWindowUiaName,
                    AutomationId = observation.ForegroundWindowUiaAutomationId,
                    ClassName = observation.ForegroundWindowUiaClassName,
                    ControlType = observation.ForegroundWindowUiaControlType,
                    IsEnabled = observation.ForegroundWindowUiaIsEnabled,
                    CandidateElements = observation.ForegroundWindowCandidateElements,
                },
            };

            File.WriteAllText(
                manifestFilePath,
                JsonSerializer.Serialize(manifest, SerializerOptions));

            return new ObservationManifestSaveResult
            {
                ManifestFilePath = manifestFilePath,
                ScreenshotStatus = manifest.ScreenshotStatus,
                ScreenshotLocalPath = screenshotLocalPath,
                AutomationSummary =
                    $"uia_name={observation.ForegroundWindowUiaName}\nuia_control_type={observation.ForegroundWindowUiaControlType}\nuia_class_name={observation.ForegroundWindowUiaClassName}\nuia_automation_id={observation.ForegroundWindowUiaAutomationId}\nuia_child_count={observation.ForegroundWindowUiaChildCount}\nuia_child_summary={observation.ForegroundWindowUiaChildSummary}\ncandidate_element_count={observation.ForegroundWindowCandidateElements.Count}",
                AutomationControlType = observation.ForegroundWindowUiaControlType,
                AutomationClassName = observation.ForegroundWindowUiaClassName,
                AutomationId = observation.ForegroundWindowUiaAutomationId,
            };
        }
        catch
        {
            // Keep manifest persistence isolated from the main analyze flow.
            return new ObservationManifestSaveResult
            {
                ManifestFilePath = null,
                ScreenshotStatus = "manifest-save-failed",
                ScreenshotLocalPath = null,
                AutomationSummary =
                    "uia_name=unknown-uia-name\nuia_control_type=unknown-control-type\nuia_class_name=unknown-class-name\nuia_automation_id=unknown-automation-id\nuia_child_count=0\nuia_child_summary=unknown-children",
                AutomationControlType = "unknown-control-type",
                AutomationClassName = "unknown-class-name",
                AutomationId = "unknown-automation-id",
            };
        }
    }

    private static string GetManifestDirectoryPath(string capturedAtUtc)
    {
        string baseDirectoryPath = GetObservationBaseDirectoryPath(ManifestFolderName);

        if (DateTime.TryParse(
            capturedAtUtc,
            null,
            DateTimeStyles.RoundtripKind,
            out DateTime parsedCapturedAt))
        {
            return Path.Combine(baseDirectoryPath, parsedCapturedAt.ToString("yyyyMMdd"));
        }

        return Path.Combine(baseDirectoryPath, FallbackDateFolder);
    }

    private static string? TryCaptureScreenshot(ObservationDto observation)
    {
        try
        {
            string screenshotDirectoryPath = GetDatedDirectoryPath(
                observation.CapturedAtUtc,
                ScreenshotFolderName);
            Directory.CreateDirectory(screenshotDirectoryPath);

            Rectangle primaryBounds = Screen.PrimaryScreen?.Bounds ?? Rectangle.Empty;
            if (primaryBounds.Width <= 0 || primaryBounds.Height <= 0)
            {
                return null;
            }

            string screenshotFilePath = Path.Combine(
                screenshotDirectoryPath,
                $"{SanitizeFileName(observation.ScreenshotRef)}.png");

            using Bitmap bitmap = new(primaryBounds.Width, primaryBounds.Height);
            using Graphics graphics = Graphics.FromImage(bitmap);
            graphics.CopyFromScreen(primaryBounds.Location, Point.Empty, primaryBounds.Size);
            bitmap.Save(screenshotFilePath, ImageFormat.Png);
            return screenshotFilePath;
        }
        catch
        {
            return null;
        }
    }

    private static string GetObservationBaseDirectoryPath(string leafFolderName)
    {
        return Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            ProductFolderName,
            ObservationFolderName,
            leafFolderName);
    }

    private static string GetDatedDirectoryPath(string capturedAtUtc, string leafFolderName)
    {
        string baseDirectoryPath = GetObservationBaseDirectoryPath(leafFolderName);

        if (DateTime.TryParse(
            capturedAtUtc,
            null,
            DateTimeStyles.RoundtripKind,
            out DateTime parsedCapturedAt))
        {
            return Path.Combine(baseDirectoryPath, parsedCapturedAt.ToString("yyyyMMdd"));
        }

        return Path.Combine(baseDirectoryPath, FallbackDateFolder);
    }

    private static string SanitizeFileName(string screenshotRef)
    {
        string sanitized = screenshotRef;
        foreach (char invalidChar in Path.GetInvalidFileNameChars())
        {
            sanitized = sanitized.Replace(invalidChar, '-');
        }

        return string.IsNullOrWhiteSpace(sanitized)
            ? "local-observation-fallback"
            : sanitized;
    }
}

public sealed class ObservationManifestRecord
{
    public string SavedAtUtc { get; init; } = string.Empty;
    public string? SessionId { get; init; }
    public string CapturedAtUtc { get; init; } = string.Empty;
    public string ForegroundWindowTitle { get; init; } = string.Empty;
    public int ScreenWidth { get; init; }
    public int ScreenHeight { get; init; }
    public string ScreenshotRef { get; init; } = string.Empty;
    public string ScreenshotStatus { get; init; } = string.Empty;
    public string? ScreenshotLocalPath { get; init; }
    public ObservationAutomationRecord ForegroundWindowAutomation { get; init; } = new();
}

public sealed class ObservationManifestSaveResult
{
    public string? ManifestFilePath { get; init; }
    public string ScreenshotStatus { get; init; } = string.Empty;
    public string? ScreenshotLocalPath { get; init; }
    public string AutomationSummary { get; init; } = string.Empty;
    public string AutomationControlType { get; init; } = string.Empty;
    public string AutomationClassName { get; init; } = string.Empty;
    public string AutomationId { get; init; } = string.Empty;
}

public sealed class ObservationAutomationRecord
{
    public string Name { get; init; } = string.Empty;
    public string AutomationId { get; init; } = string.Empty;
    public string ClassName { get; init; } = string.Empty;
    public string ControlType { get; init; } = string.Empty;
    public bool IsEnabled { get; init; }
    public List<ObservationCandidateElementDto> CandidateElements { get; init; } = [];
}
