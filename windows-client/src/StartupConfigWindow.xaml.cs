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

        if (string.IsNullOrWhiteSpace(modelType) || string.IsNullOrWhiteSpace(apiKey))
        {
            ValidationTextBlock.Text = "模型类型和 API Key 都必须由人工手动输入后才能继续。";
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
