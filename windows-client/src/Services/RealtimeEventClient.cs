using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using WindowsStepGuide.Client.Contracts;

namespace WindowsStepGuide.Client.Services;

public interface IRealtimeEventClient
{
    Task RunAsync(
        Action<RealtimeEventDto> onEvent,
        Action onConnected,
        Action<string> onDisconnected,
        CancellationToken cancellationToken);
}

public sealed class RealtimeEventClient : IRealtimeEventClient
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
    };

    private readonly IReadOnlyList<Uri> _wsUris;

    public RealtimeEventClient(Uri backendBaseAddress)
    {
        _wsUris = BuildWebSocketUris(backendBaseAddress);
    }

    public async Task RunAsync(
        Action<RealtimeEventDto> onEvent,
        Action onConnected,
        Action<string> onDisconnected,
        CancellationToken cancellationToken)
    {
        string? lastError = null;
        foreach (Uri wsUri in _wsUris)
        {
            using ClientWebSocket socket = new();
            try
            {
                await socket.ConnectAsync(wsUri, cancellationToken);
                onConnected();
                await ReceiveLoopAsync(socket, onEvent, cancellationToken);
                onDisconnected("server closed");
                return;
            }
            catch (OperationCanceledException)
            {
                onDisconnected("cancelled");
                return;
            }
            catch (Exception ex)
            {
                lastError = ex.Message;
            }
        }

        onDisconnected(lastError ?? "connect failed");
    }

    private static IReadOnlyList<Uri> BuildWebSocketUris(Uri backendBaseAddress)
    {
        string scheme = backendBaseAddress.Scheme.Equals("https", StringComparison.OrdinalIgnoreCase)
            ? "wss"
            : "ws";
        return
        [
            new UriBuilder(backendBaseAddress)
            {
                Scheme = scheme,
                Path = "api/ws/events",
            }.Uri,
            new UriBuilder(backendBaseAddress)
            {
                Scheme = scheme,
                Path = "ws/events",
            }.Uri,
        ];
    }

    private static async Task ReceiveLoopAsync(
        ClientWebSocket socket,
        Action<RealtimeEventDto> onEvent,
        CancellationToken cancellationToken)
    {
        ArraySegment<byte> buffer = new(new byte[4096]);
        while (socket.State == WebSocketState.Open && !cancellationToken.IsCancellationRequested)
        {
            StringBuilder payloadBuilder = new();
            WebSocketReceiveResult result;
            do
            {
                result = await socket.ReceiveAsync(buffer, cancellationToken);
                if (result.MessageType == WebSocketMessageType.Close)
                {
                    return;
                }

                string chunk = Encoding.UTF8.GetString(buffer.Array!, 0, result.Count);
                payloadBuilder.Append(chunk);
            } while (!result.EndOfMessage);

            RealtimeEventDto? eventPayload = JsonSerializer.Deserialize<RealtimeEventDto>(
                payloadBuilder.ToString(),
                JsonOptions);
            if (eventPayload is not null)
            {
                onEvent(eventPayload);
            }
        }
    }
}
