import Foundation
import Network

/// Envia gestos a Rhino por UDP (JSON, un mensaje por datagrama).
final class RhinoLink: ObservableObject {
    @Published var status = "Desconectado"
    private var connection: NWConnection?

    func connect(host: String, port: UInt16) {
        connection?.cancel()
        guard !host.isEmpty, let nwPort = NWEndpoint.Port(rawValue: port) else {
            status = "IP o puerto invalido"
            return
        }
        let conn = NWConnection(host: NWEndpoint.Host(host), port: nwPort, using: .udp)
        conn.stateUpdateHandler = { [weak self] state in
            DispatchQueue.main.async {
                switch state {
                case .ready: self?.status = "Listo: \(host):\(port)"
                case .failed(let error): self?.status = "Error: \(error.localizedDescription)"
                case .waiting(let error): self?.status = "Esperando: \(error.localizedDescription)"
                default: break
                }
            }
        }
        conn.start(queue: .global(qos: .userInteractive))
        connection = conn
    }

    func orbit(dx: Double, dy: Double) { send(["type": "orbit", "dx": dx, "dy": dy]) }
    func pan(dx: Double, dy: Double) { send(["type": "pan", "dx": dx, "dy": dy]) }
    func zoom(factor: Double) { send(["type": "zoom", "factor": factor]) }
    func view(_ name: String) { send(["type": "view", "name": name]) }
    func extents() { send(["type": "extents"]) }

    private func send(_ message: [String: Any]) {
        guard let conn = connection,
              let data = try? JSONSerialization.data(withJSONObject: message) else { return }
        conn.send(content: data, completion: .contentProcessed { _ in })
    }
}
