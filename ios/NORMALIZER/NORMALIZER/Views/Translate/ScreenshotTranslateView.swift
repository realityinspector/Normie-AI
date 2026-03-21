import SwiftUI
import PhotosUI

struct ScreenshotTranslateView: View {
    @State private var vm = ScreenshotTranslateViewModel()
    @State private var selectedItem: PhotosPickerItem?

    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                // Image selection
                VStack(spacing: 12) {
                    if let image = vm.selectedImage {
                        Image(uiImage: image)
                            .resizable()
                            .scaledToFit()
                            .frame(maxHeight: 250)
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                    } else {
                        RoundedRectangle(cornerRadius: 12)
                            .fill(.ultraThinMaterial)
                            .frame(height: 200)
                            .overlay {
                                VStack(spacing: 8) {
                                    Image(systemName: "photo.on.rectangle.angled")
                                        .font(.largeTitle)
                                        .foregroundStyle(.secondary)
                                    Text("Select an image to translate")
                                        .font(.subheadline)
                                        .foregroundStyle(.secondary)
                                }
                            }
                    }

                    HStack(spacing: 16) {
                        PhotosPicker(selection: $selectedItem, matching: .images) {
                            Label("Choose Photo", systemImage: "photo.fill")
                                .frame(maxWidth: .infinity)
                                .padding()
                                .background(.ultraThinMaterial)
                                .clipShape(RoundedRectangle(cornerRadius: 10))
                        }

                        Button {
                            vm.showCamera = true
                        } label: {
                            Label("Camera", systemImage: "camera.fill")
                                .frame(maxWidth: .infinity)
                                .padding()
                                .background(.ultraThinMaterial)
                                .clipShape(RoundedRectangle(cornerRadius: 10))
                        }
                    }
                }

                // Direction picker
                DirectionPicker(direction: $vm.direction)

                // Translate button
                Button {
                    Task { await vm.translate() }
                } label: {
                    HStack {
                        if vm.isLoading {
                            ProgressView()
                                .tint(.white)
                        }
                        Text("Translate Screenshot")
                            .bold()
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(vm.selectedImage == nil ? Color.gray : Color.accentColor)
                    .foregroundStyle(.white)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                }
                .disabled(vm.selectedImage == nil || vm.isLoading)

                // Result
                if let result = vm.result {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Extracted Text")
                            .font(.subheadline.bold())
                        Text(result.extractedText)
                            .padding()
                            .background(.ultraThinMaterial)
                            .clipShape(RoundedRectangle(cornerRadius: 8))

                        TranslationResultView(
                            original: result.extractedText,
                            translated: result.translatedText,
                            creditsRemaining: result.creditsRemaining
                        )
                    }
                }

                if let error = vm.error {
                    Text(error)
                        .font(.caption)
                        .foregroundStyle(.red)
                }
            }
            .padding()
        }
        .navigationTitle("Screenshot Translate")
        .onChange(of: selectedItem) { _, newItem in
            Task {
                if let data = try? await newItem?.loadTransferable(type: Data.self),
                   let image = UIImage(data: data) {
                    vm.selectedImage = image
                }
            }
        }
        .fullScreenCover(isPresented: $vm.showCamera) {
            CameraView(image: Binding(
                get: { vm.selectedImage },
                set: { vm.selectedImage = $0 }
            ))
        }
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button("Clear") { vm.clear() }
            }
        }
    }
}

// MARK: - Camera UIKit wrapper

struct CameraView: UIViewControllerRepresentable {
    @Binding var image: UIImage?
    @Environment(\.dismiss) private var dismiss

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = .camera
        picker.delegate = context.coordinator
        return picker
    }

    func updateUIViewController(_ uiViewController: UIImagePickerController, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    class Coordinator: NSObject, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
        let parent: CameraView

        init(_ parent: CameraView) {
            self.parent = parent
        }

        func imagePickerController(_ picker: UIImagePickerController, didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]) {
            if let image = info[.originalImage] as? UIImage {
                parent.image = image
            }
            parent.dismiss()
        }

        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            parent.dismiss()
        }
    }
}
