using System.Windows;
using System.Windows.Controls;
using WindowsStepGuide.Client.Services;

namespace WindowsStepGuide.Client;

public partial class StartupConfigWindow : Window
{
    private const string OpenAiProvider = "openai";
    private const string OpenAiCompatibleProvider = "openai_compatible";
    private const string DefaultOpenAiBaseUrl = "https://api.openai.com/v1/responses";
    private const string DefaultDashScopeBaseUrl = "https://coding.dashscope.aliyuncs.com/v1/chat/completions";

    public StartupConfigWindow()
    {
        InitializeComponent();
        AuthModeComboBox.SelectedIndex = 0;
        ProviderComboBox.SelectedIndex = 0;
        BaseUrlTextBox.Text = DefaultOpenAiBaseUrl;
        ModelTypeTextBox.Text = "gpt-4.1";
        CredentialLabelTextBlock.Text = "会员令牌（可选）";
    }

    public RuntimeModelConfig? RuntimeModelConfig { get; private set; }

    private void ConfirmButton_Click(object sender, RoutedEventArgs e)
    {
        string provider = GetSelectedTag(ProviderComboBox, OpenAiProvider);
        string authMode = GetSelectedTag(AuthModeComboBox, "member_token");
        string modelType = ModelTypeTextBox.Text.Trim();
        string baseUrl = BaseUrlTextBox.Text.Trim();
        string apiKey = ApiKeyPasswordBox.Password.Trim();

        if (string.IsNullOrWhiteSpace(modelType) || string.IsNullOrWhiteSpace(baseUrl))
        {
            ValidationTextBlock.Text = "模型类型和 Base URL 不能为空。";
            return;
        }

        RuntimeModelConfig = new RuntimeModelConfig
        {
            Provider = provider,
            BaseUrl = baseUrl,
            AuthMode = authMode,
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

    private void AuthModeComboBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        string authMode = GetSelectedTag(AuthModeComboBox, "member_token");
        CredentialLabelTextBlock.Text = authMode == "member_token"
            ? "会员令牌（可选）"
            : "API Key（可选）";
    }

    private void ProviderComboBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (ProviderComboBox.SelectedItem is not ComboBoxItem selectedItem)
        {
            return;
        }

        string displayName = (selectedItem.Content as string ?? string.Empty).Trim();
        string provider = (selectedItem.Tag as string ?? OpenAiCompatibleProvider).Trim();
        if (string.IsNullOrWhiteSpace(provider))
        {
            provider = OpenAiCompatibleProvider;
        }

        if (displayName.Contains("OpenAI", StringComparison.OrdinalIgnoreCase))
        {
            BaseUrlTextBox.Text = DefaultOpenAiBaseUrl;
            if (string.IsNullOrWhiteSpace(ModelTypeTextBox.Text))
            {
                ModelTypeTextBox.Text = "gpt-4.1";
            }

            return;
        }

        if (displayName.Contains("百炼", StringComparison.OrdinalIgnoreCase)
            || displayName.Contains("DashScope", StringComparison.OrdinalIgnoreCase))
        {
            BaseUrlTextBox.Text = DefaultDashScopeBaseUrl;
            if (string.IsNullOrWhiteSpace(ModelTypeTextBox.Text) || ModelTypeTextBox.Text == "gpt-4.1")
            {
                ModelTypeTextBox.Text = "qwen3-coder-plus";
            }
            return;
        }

        if (provider == OpenAiProvider)
        {
            BaseUrlTextBox.Text = DefaultOpenAiBaseUrl;
        }
    }

    private static string GetSelectedTag(ComboBox comboBox, string fallback)
    {
        if (comboBox.SelectedItem is ComboBoxItem selectedItem)
        {
            string value = (selectedItem.Tag as string ?? string.Empty).Trim();
            if (!string.IsNullOrWhiteSpace(value))
            {
                return value;
            }
        }

        return fallback;
    }
}
