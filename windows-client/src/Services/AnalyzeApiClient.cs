using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using WindowsStepGuide.Client.Contracts;

namespace WindowsStepGuide.Client.Services;

public interface IAnalyzeApiClient
{
    Task<NextStepResponse> AnalyzeAsync(AnalyzeRequest request, CancellationToken cancellationToken = default);
}

public sealed class AnalyzeApiClient : IAnalyzeApiClient
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };

    private readonly HttpClient _httpClient;

    public AnalyzeApiClient(Uri baseAddress)
    {
        _httpClient = new HttpClient
        {
            BaseAddress = baseAddress,
        };
    }

    public async Task<NextStepResponse> AnalyzeAsync(AnalyzeRequest request, CancellationToken cancellationToken = default)
    {
        using HttpResponseMessage response = await _httpClient.PostAsJsonAsync(
            "api/analyze",
            new { task_text = request.TaskText },
            JsonOptions,
            cancellationToken);

        response.EnsureSuccessStatusCode();

        NextStepResponse? payload = await response.Content.ReadFromJsonAsync<NextStepResponse>(JsonOptions, cancellationToken);
        return payload ?? new NextStepResponse
        {
            Instruction = "后端返回为空。",
        };
    }
}
