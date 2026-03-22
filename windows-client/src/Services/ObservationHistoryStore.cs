using System.Collections.ObjectModel;
using WindowsStepGuide.Client.Contracts;

namespace WindowsStepGuide.Client.Services;

public sealed class ObservationHistoryItem
{
    public string CapturedAtUtc { get; init; } = string.Empty;
    public string ForegroundWindowTitle { get; init; } = string.Empty;
    public int ScreenWidth { get; init; }
    public int ScreenHeight { get; init; }
    public string ScreenshotRef { get; init; } = string.Empty;
    public string ScreenshotStatus { get; init; } = string.Empty;
    public string? ScreenshotLocalPath { get; init; }
    public string AutomationControlType { get; init; } = string.Empty;
    public string AutomationClassName { get; init; } = string.Empty;
    public string AutomationId { get; init; } = string.Empty;
}

public interface IObservationHistoryStore
{
    ReadOnlyObservableCollection<ObservationHistoryItem> Items { get; }
    void Add(
        ObservationDto observation,
        string screenshotStatus,
        string? screenshotLocalPath,
        string automationControlType,
        string automationClassName,
        string automationId);
}

public sealed class ObservationHistoryStore : IObservationHistoryStore
{
    private const int MaxItems = 5;

    private readonly ObservableCollection<ObservationHistoryItem> _items = [];
    private readonly ReadOnlyObservableCollection<ObservationHistoryItem> _readOnlyItems;

    public ObservationHistoryStore()
    {
        _readOnlyItems = new ReadOnlyObservableCollection<ObservationHistoryItem>(_items);
    }

    public ReadOnlyObservableCollection<ObservationHistoryItem> Items => _readOnlyItems;

    public void Add(
        ObservationDto observation,
        string screenshotStatus,
        string? screenshotLocalPath,
        string automationControlType,
        string automationClassName,
        string automationId)
    {
        try
        {
            _items.Insert(0, new ObservationHistoryItem
            {
                CapturedAtUtc = observation.CapturedAtUtc,
                ForegroundWindowTitle = observation.ForegroundWindowTitle,
                ScreenWidth = observation.ScreenWidth,
                ScreenHeight = observation.ScreenHeight,
                ScreenshotRef = observation.ScreenshotRef,
                ScreenshotStatus = screenshotStatus,
                ScreenshotLocalPath = screenshotLocalPath,
                AutomationControlType = automationControlType,
                AutomationClassName = automationClassName,
                AutomationId = automationId,
            });

            while (_items.Count > MaxItems)
            {
                _items.RemoveAt(_items.Count - 1);
            }
        }
        catch
        {
            // Keep the debug-only history isolated from the main analyze flow.
        }
    }
}
