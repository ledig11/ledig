using System.Runtime.InteropServices;
using System.Windows.Automation;
using WindowsStepGuide.Client.Contracts;

namespace WindowsStepGuide.Client.Services;

public interface IForegroundWindowAutomationProvider
{
    ForegroundWindowAutomationSnapshot Capture();
}

public sealed class ForegroundWindowAutomationProvider : IForegroundWindowAutomationProvider
{
    private const int MaxCandidateElements = 8;

    public ForegroundWindowAutomationSnapshot Capture()
    {
        try
        {
            nint foregroundWindowHandle = GetForegroundWindow();
            if (foregroundWindowHandle == nint.Zero)
            {
                return ForegroundWindowAutomationSnapshot.Fallback();
            }

            AutomationElement? element = AutomationElement.FromHandle(foregroundWindowHandle);
            if (element is null)
            {
                return ForegroundWindowAutomationSnapshot.Fallback();
            }

            AutomationElementInformation current = element.Current;
            return new ForegroundWindowAutomationSnapshot
            {
                Name = Normalize(current.Name, "unknown-uia-name"),
                AutomationId = Normalize(current.AutomationId, "unknown-automation-id"),
                ClassName = Normalize(current.ClassName, "unknown-class-name"),
                ControlType = current.ControlType?.ProgrammaticName ?? "unknown-control-type",
                IsEnabled = current.IsEnabled,
                ChildCount = GetChildCount(element),
                ChildSummary = BuildChildSummary(element),
                CandidateElements = BuildCandidateElements(element),
            };
        }
        catch
        {
            return ForegroundWindowAutomationSnapshot.Fallback();
        }
    }

    private static string Normalize(string? value, string fallback)
    {
        return string.IsNullOrWhiteSpace(value) ? fallback : value;
    }

    private static int GetChildCount(AutomationElement element)
    {
        try
        {
            return element.FindAll(TreeScope.Children, Condition.TrueCondition).Count;
        }
        catch
        {
            return 0;
        }
    }

    private static string BuildChildSummary(AutomationElement element)
    {
        try
        {
            AutomationElementCollection children = element.FindAll(TreeScope.Children, Condition.TrueCondition);
            if (children.Count == 0)
            {
                return "no-direct-children";
            }

            List<string> childParts = new();
            int maxChildren = Math.Min(children.Count, 5);
            for (int index = 0; index < maxChildren; index++)
            {
                AutomationElementInformation child = children[index].Current;
                string controlType = child.ControlType?.ProgrammaticName ?? "unknown-control-type";
                string name = Normalize(child.Name, "unnamed-child");
                childParts.Add($"{controlType}:{name}");
            }

            if (children.Count > maxChildren)
            {
                childParts.Add($"...+{children.Count - maxChildren} more");
            }

            return string.Join(" | ", childParts);
        }
        catch
        {
            return "child-summary-unavailable";
        }
    }

    private static List<ObservationCandidateElementDto> BuildCandidateElements(AutomationElement rootElement)
    {
        try
        {
            AutomationElementCollection children = rootElement.FindAll(TreeScope.Children, Condition.TrueCondition);
            List<ObservationCandidateElementDto> candidates = [];
            int maxChildren = Math.Min(children.Count, MaxCandidateElements);

            for (int index = 0; index < maxChildren; index++)
            {
                AutomationElement child = children[index];
                AutomationElementInformation current = child.Current;
                candidates.Add(new ObservationCandidateElementDto
                {
                    Name = Normalize(current.Name, "unnamed-child"),
                    AutomationId = Normalize(current.AutomationId, "unknown-automation-id"),
                    ClassName = Normalize(current.ClassName, "unknown-class-name"),
                    ControlType = current.ControlType?.ProgrammaticName ?? "unknown-control-type",
                    IsEnabled = current.IsEnabled,
                    IsOffscreen = current.IsOffscreen,
                    IsKeyboardFocusable = current.IsKeyboardFocusable,
                    HasKeyboardFocus = current.HasKeyboardFocus,
                    UiPath = $"foreground-window/child[{index}]",
                    BoundingRect = CreateRect(current.BoundingRectangle),
                });
            }

            return candidates;
        }
        catch
        {
            return [];
        }
    }

    private static RectResponse CreateRect(System.Windows.Rect boundingRectangle)
    {
        return new RectResponse
        {
            X = (int)Math.Round(boundingRectangle.X),
            Y = (int)Math.Round(boundingRectangle.Y),
            Width = Math.Max((int)Math.Round(boundingRectangle.Width), 0),
            Height = Math.Max((int)Math.Round(boundingRectangle.Height), 0),
        };
    }

    [DllImport("user32.dll")]
    private static extern nint GetForegroundWindow();
}

public sealed class ForegroundWindowAutomationSnapshot
{
    public string Name { get; init; } = string.Empty;
    public string AutomationId { get; init; } = string.Empty;
    public string ClassName { get; init; } = string.Empty;
    public string ControlType { get; init; } = string.Empty;
    public bool IsEnabled { get; init; }
    public int ChildCount { get; init; }
    public string ChildSummary { get; init; } = string.Empty;
    public List<ObservationCandidateElementDto> CandidateElements { get; init; } = [];

    public static ForegroundWindowAutomationSnapshot Fallback()
    {
        return new ForegroundWindowAutomationSnapshot
        {
            Name = "unknown-uia-name",
            AutomationId = "unknown-automation-id",
            ClassName = "unknown-class-name",
            ControlType = "unknown-control-type",
            IsEnabled = false,
            ChildCount = 0,
            ChildSummary = "unknown-children",
            CandidateElements = [],
        };
    }
}
