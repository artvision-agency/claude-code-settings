import Vision
import AppKit
import Foundation

guard CommandLine.arguments.count > 1 else {
    FileHandle.standardError.write("Usage: swift ocr.swift <image_path>\n".data(using: .utf8)!)
    exit(1)
}

let url = URL(fileURLWithPath: CommandLine.arguments[1])
guard let image = NSImage(contentsOf: url),
      let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    FileHandle.standardError.write("Can't load image\n".data(using: .utf8)!)
    exit(2)
}

let request = VNRecognizeTextRequest { (request, error) in
    if let err = error {
        FileHandle.standardError.write("OCR error: \(err)\n".data(using: .utf8)!)
        return
    }
    guard let observations = request.results as? [VNRecognizedTextObservation] else { return }
    let strings = observations.compactMap { $0.topCandidates(1).first?.string }
    print(strings.joined(separator: "\n"))
}
request.recognitionLanguages = ["ru-RU", "en-US"]
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true

let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
do {
    try handler.perform([request])
} catch {
    FileHandle.standardError.write("Perform failed: \(error)\n".data(using: .utf8)!)
    exit(3)
}
