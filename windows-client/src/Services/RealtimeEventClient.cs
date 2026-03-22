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

    private readonly Uri _wsUri;

    public RealtimeEventClient(Uri backendBaseAddress)
    {
        _wsUri = BuildWebSocketUri(backendBaseAddress);
    }

    public async Task RunAsync(
        Action<RealtimeEventDto> onEvent,
        Action onConnected,
        Action<string> onDisconnected,
        CancellationToken cancellationToken)
    {
        using ClientWebSocket socket = new();
        try
        {
            await socket.ConnectAsync(_wsUri, cancellationToken);
            onConnected();
            await ReceiveLoopAsync(socket, onEvent, cancellationToken);
            onDisconnected("server closed");
        }
        catch (OperationCanceledException)
        {
            onDisconnected("cancelled");
        }
        catch (Exception ex)
        {
            onDisconnected(ex.Message);
        }
    }

    private static Uri BuildWebSocketUri(Uri backendBaseAddress)
    {
        string scheme = backendBaseAddress.Scheme.Equals("https", StringComparison.OrdinalIgnoreCase)
            ? "wss"
            : "ws";
        UriBuilder builder = new(backendBaseAddress)
        {
            Scheme = scheme,
            Path = "api/ws/events",
        };
        return builder.Uri;
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
