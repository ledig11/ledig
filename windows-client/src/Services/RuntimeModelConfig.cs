namespace WindowsStepGuide.Client.Services;

public sealed class RuntimeModelConfig
{
    public string Provider { get; init; } = "openai";
    public string BaseUrl { get; init; } = string.Empty;
    public string AuthMode { get; init; } = "api_key";
    public string ModelType { get; init; } = string.Empty;
    public string ApiKey { get; init; } = string.Empty;

    public string GetMaskedApiKey()
    {
        if (string.IsNullOrWhiteSpace(ApiKey))
        {
            return "not-set";
        }

        if (ApiKey.Length <= 6)
        {
            return "******";
        }

        return $"{ApiKey[..3]}***{ApiKey[^3..]}";
    }
}
