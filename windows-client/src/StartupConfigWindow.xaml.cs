using System.Windows;
using WindowsStepGuide.Client.Services;

namespace WindowsStepGuide.Client;

public partial class StartupConfigWindow : Window
{
    public StartupConfigWindow()
    {
        InitializeComponent();
        ModelTypeTextBox.Text = "gpt-4.1";
    }

    public RuntimeModelConfig? RuntimeModelConfig { get; private set; }

    private void ConfirmButton_Click(object sender, RoutedEventArgs e)
    {
        string modelType = ModelTypeTextBox.Text.Trim();
        string apiKey = ApiKeyPasswordBox.Password.Trim();

        if (string.IsNullOrWhiteSpace(modelType))
        {
            ValidationTextBlock.Text = "模型类型不能为空。";
            return;
        }

        RuntimeModelConfig = new RuntimeModelConfig
        {
            ModelType = modelType,
            ApiKey = apiKey,
        };

        DialogResult = true;
        Close();
    }

    private void CancelButton_Click(object sender, RoutedEventArgs e)
    {
        DialogResult = false;
        Close();
    }
}
