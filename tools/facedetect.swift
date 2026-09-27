// Детектор лиц через macOS Vision: для каждого файла печатает центр и размер самого крупного лица
// в долях кадра (начало координат — левый верхний угол) или «-». Сборка: swiftc -O -o facedetect tools/facedetect.swift
import Foundation
import Vision
import AppKit

for path in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        print("\(path) ERR"); continue
    }
    let req = VNDetectFaceRectanglesRequest()
    let handler = VNImageRequestHandler(cgImage: cg, options: [:])
    try? handler.perform([req])
    let faces = (req.results ?? []).sorted { $0.boundingBox.width > $1.boundingBox.width }
    let name = (path as NSString).lastPathComponent
    if let f = faces.first {
        let b = f.boundingBox   // normalized, origin bottom-left
        print(String(format: "%@ %.3f %.3f %.3f %.3f", name, b.midX, 1 - b.midY, b.width, b.height))
    } else {
        print("\(name) -")
    }
}
