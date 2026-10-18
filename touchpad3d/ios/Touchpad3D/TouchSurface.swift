import SwiftUI
import UIKit

/// Lienzo tactil: 1 dedo orbita, 2 dedos desplazan (pan), pellizco hace zoom, doble toque = zoom extents.
struct TouchSurface: UIViewRepresentable {
    let link: RhinoLink

    func makeUIView(context: Context) -> UIView {
        let view = UIView()
        view.backgroundColor = UIColor(white: 0.08, alpha: 1)
        view.isMultipleTouchEnabled = true

        let orbit = UIPanGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.orbit(_:)))
        orbit.minimumNumberOfTouches = 1
        orbit.maximumNumberOfTouches = 1

        let pan = UIPanGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.pan(_:)))
        pan.minimumNumberOfTouches = 2
        pan.maximumNumberOfTouches = 2
        pan.delegate = context.coordinator

        let pinch = UIPinchGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.pinch(_:)))
        pinch.delegate = context.coordinator

        let doubleTap = UITapGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.doubleTap(_:)))
        doubleTap.numberOfTapsRequired = 2

        [orbit, pan, pinch, doubleTap].forEach(view.addGestureRecognizer)
        return view
    }

    func updateUIView(_ uiView: UIView, context: Context) {}

    func makeCoordinator() -> Coordinator { Coordinator(link: link) }

    final class Coordinator: NSObject, UIGestureRecognizerDelegate {
        let link: RhinoLink
        init(link: RhinoLink) { self.link = link }

        /// Traslacion incremental normalizada al tamano del lienzo.
        private func delta(_ g: UIPanGestureRecognizer) -> (Double, Double)? {
            guard let view = g.view, view.bounds.width > 0, view.bounds.height > 0 else { return nil }
            let t = g.translation(in: view)
            g.setTranslation(.zero, in: view)
            return (Double(t.x / view.bounds.width), Double(t.y / view.bounds.height))
        }

        @objc func orbit(_ g: UIPanGestureRecognizer) {
            if let (dx, dy) = delta(g) { link.orbit(dx: dx, dy: dy) }
        }

        @objc func pan(_ g: UIPanGestureRecognizer) {
            if let (dx, dy) = delta(g) { link.pan(dx: dx, dy: dy) }
        }

        @objc func pinch(_ g: UIPinchGestureRecognizer) {
            link.zoom(factor: Double(g.scale))
            g.scale = 1
        }

        @objc func doubleTap(_ g: UITapGestureRecognizer) { link.extents() }

        func gestureRecognizer(_ a: UIGestureRecognizer, shouldRecognizeSimultaneouslyWith b: UIGestureRecognizer) -> Bool { true }
    }
}
