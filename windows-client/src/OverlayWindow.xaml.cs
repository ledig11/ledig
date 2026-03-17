using System.Windows;

namespace WindowsStepGuide.Client;

public partial class OverlayWindow : Window
{
    private const double WindowPadding = 6;

    public OverlayWindow()
    {
        InitializeComponent();
    }

    public void ShowHighlight(double left, double top, double width, double height)
    {
        if (width <= 0 || height <= 0)
        {
            HideHighlight();
            return;
        }

        Left = Math.Max(left - WindowPadding, 0);
        Top = Math.Max(top - WindowPadding, 0);
        Width = Math.Max(width + (WindowPadding * 2), 20);
        Height = Math.Max(height + (WindowPadding * 2), 20);

        if (!IsVisible)
        {
            Show();
        }
    }

    public void HideHighlight()
    {
        if (IsVisible)
        {
            Hide();
        }
    }
}
