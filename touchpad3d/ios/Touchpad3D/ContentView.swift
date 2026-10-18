import SwiftUI

struct ContentView: View {
    @StateObject private var link = RhinoLink()
    @AppStorage("host") private var host = ""
    @AppStorage("port") private var port = 9876

    private let views = [("Top", "top"), ("Front", "front"), ("Right", "right"), ("Persp", "perspective")]

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 12) {
                TextField("IP de la PC con Rhino", text: $host)
                    .textFieldStyle(.roundedBorder)
                    .keyboardType(.numbersAndPunctuation)
                    .autocorrectionDisabled()
                    .frame(maxWidth: 220)
                TextField("Puerto", value: $port, format: .number.grouping(.never))
                    .textFieldStyle(.roundedBorder)
                    .keyboardType(.numberPad)
                    .frame(width: 80)
                Button("Conectar") { link.connect(host: host, port: UInt16(clamping: port)) }
                    .buttonStyle(.borderedProminent)
                Text(link.status).font(.footnote).foregroundStyle(.secondary).lineLimit(1)
                Spacer()
                ForEach(views, id: \.1) { title, name in
                    Button(title) { link.view(name) }.buttonStyle(.bordered)
                }
                Button("Extents") { link.extents() }.buttonStyle(.bordered)
            }
            .padding(10)

            TouchSurface(link: link)
                .overlay(alignment: .bottom) {
                    Text("1 dedo: orbitar  ·  2 dedos: desplazar  ·  pellizco: zoom  ·  doble toque: extents")
                        .font(.caption).foregroundStyle(.tertiary).padding(8)
                        .allowsHitTesting(false)
                }
        }
        .onAppear { if !host.isEmpty { link.connect(host: host, port: UInt16(clamping: port)) } }
    }
}
