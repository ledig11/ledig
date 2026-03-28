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
    private const int MaxCandidateElements = 24;
    private const int MaxScanDepth = 6;
    private const int MaxScannedNodes = 400;

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

            var current = element.Current;
            return new ForegroundWindowAutomationSnapshot
            {
                Name = Normalize(current.Name, "unknown-uia-name"),
                AutomationId = Normalize(current.AutomationId, "unknown-automation-id"),
                ClassName = Normalize(current.ClassName, "unknown-class-name"),
                ControlType = current.ControlType?.ProgrammaticName ?? "unknown-control-type",
                IsEnabled = current.IsEnabled,
                ChildCount = GetChildCount(element),
                ChildSummary = BuildChildSummary(element),
                CandidateElements = BuildCandidateElements(element, out int scannedNodeCount, out int maxDepthReached),
                ScannedNodeCount = scannedNodeCount,
                MaxDepthReached = maxDepthReached,
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
                var child = children[index].Current;
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

    private static List<ObservationCandidateElementDto> BuildCandidateElements(
        AutomationElement rootElement,
        out int scannedNodeCount,
        out int maxDepthReached)
    {
        scannedNodeCount = 0;
        maxDepthReached = 0;
        List<CandidateScoredItem> scoredCandidates = [];

        try
        {
            Queue<TraversalItem> queue = new();
            queue.Enqueue(new TraversalItem(rootElement, "foreground-window", 0));

            while (queue.Count > 0 && scannedNodeCount < MaxScannedNodes)
            {
                TraversalItem currentItem = queue.Dequeue();
                scannedNodeCount++;
                maxDepthReached = Math.Max(maxDepthReached, currentItem.Depth);

                if (currentItem.Depth >= MaxScanDepth)
                {
                    continue;
                }

                AutomationElementCollection children;
                try
                {
                    children = currentItem.Element.FindAll(TreeScope.Children, Condition.TrueCondition);
                }
                catch
                {
                    continue;
                }

                int childCount = children.Count;
                for (int index = 0; index < childCount; index++)
                {
                    AutomationElement child = children[index];
                    string childPath = $"{currentItem.UiPath}/child[{index}]";
                    int childDepth = currentItem.Depth + 1;
                    queue.Enqueue(new TraversalItem(child, childPath, childDepth));

                    if (!TryCreateCandidate(child, childPath, out ObservationCandidateElementDto candidate, out int score))
                    {
                        continue;
                    }

                    scoredCandidates.Add(new CandidateScoredItem(candidate, score, childDepth));
                }
            }

            return scoredCandidates
                .OrderByDescending(item => item.Score)
                .ThenBy(item => item.Depth)
                .Take(MaxCandidateElements)
                .Select(item => item.Candidate)
                .ToList();
        }
        catch
        {
            scannedNodeCount = 0;
            maxDepthReached = 0;
            return [];
        }
    }

    private static bool TryCreateCandidate(
        AutomationElement element,
        string uiPath,
        out ObservationCandidateElementDto candidate,
        out int score)
    {
        candidate = null!;
        score = 0;

        System.Windows.Automation.AutomationElement.AutomationElementInformation current;
        try
        {
            // Accessing Current can throw when the element becomes unavailable mid-traversal.
            current = element.Current;
        }
        catch
        {
            return false;
        }

        RectResponse rect = CreateRect(current.BoundingRectangle);
        if (rect.Width <= 0 || rect.Height <= 0)
        {
            return false;
        }

        string name = Normalize(current.Name, "unnamed-child");
        string automationId = Normalize(current.AutomationId, "unknown-automation-id");
        string className = Normalize(current.ClassName, "unknown-class-name");
        string controlType = current.ControlType?.ProgrammaticName ?? "unknown-control-type";
        bool isEnabled = current.IsEnabled;
        bool isOffscreen = current.IsOffscreen;
        bool isKeyboardFocusable = current.IsKeyboardFocusable;
        bool hasKeyboardFocus = current.HasKeyboardFocus;

        int scoreFromControlType = GetControlTypeScore(controlType);
        bool hasIdentity = !string.Equals(name, "unnamed-child", StringComparison.Ordinal)
            || !string.Equals(automationId, "unknown-automation-id", StringComparison.Ordinal);
        int scoreFromIdentity = hasIdentity ? 3 : 0;
        int scoreFromState = (isEnabled ? 4 : 0)
            + (!isOffscreen ? 3 : 0)
            + (isKeyboardFocusable ? 2 : 0)
            + (hasKeyboardFocus ? 1 : 0);

        score = scoreFromControlType + scoreFromIdentity + scoreFromState;
        if (score < 6)
        {
            return false;
        }

        candidate = new ObservationCandidateElementDto
        {
            Name = name,
            AutomationId = automationId,
            ClassName = className,
            ControlType = controlType,
            IsEnabled = isEnabled,
            IsOffscreen = isOffscreen,
            IsKeyboardFocusable = isKeyboardFocusable,
            HasKeyboardFocus = hasKeyboardFocus,
            UiPath = uiPath,
            BoundingRect = rect,
        };
        return true;
    }

    private static int GetControlTypeScore(string controlType)
    {
        string normalized = controlType.Trim().ToLowerInvariant();
        if (normalized.Contains("button", StringComparison.Ordinal))
        {
            return 10;
        }

        if (normalized.Contains("hyperlink", StringComparison.Ordinal)
            || normalized.Contains("tabitem", StringComparison.Ordinal)
            || normalized.Contains("menuitem", StringComparison.Ordinal)
            || normalized.Contains("listitem", StringComparison.Ordinal)
            || normalized.Contains("treeitem", StringComparison.Ordinal))
        {
            return 8;
        }

        if (normalized.Contains("checkbox", StringComparison.Ordinal)
            || normalized.Contains("radiobutton", StringComparison.Ordinal)
            || normalized.Contains("togglebutton", StringComparison.Ordinal))
        {
            return 8;
        }

        if (normalized.Contains("edit", StringComparison.Ordinal)
            || normalized.Contains("combo", StringComparison.Ordinal)
            || normalized.Contains("document", StringComparison.Ordinal))
        {
            return 6;
        }

        if (normalized.Contains("pane", StringComparison.Ordinal)
            || normalized.Contains("text", StringComparison.Ordinal))
        {
            return 3;
        }

        return 1;
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

    private readonly record struct TraversalItem(AutomationElement Element, string UiPath, int Depth);
    private readonly record struct CandidateScoredItem(ObservationCandidateElementDto Candidate, int Score, int Depth);
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
    public int ScannedNodeCount { get; init; }
    public int MaxDepthReached { get; init; }

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
            ScannedNodeCount = 0,
            MaxDepthReached = 0,
        };
    }
}
