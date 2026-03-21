import SwiftUI

struct TextTranslateView: View {
    @State private var vm = TextTranslateViewModel()

    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                // Direction picker
                DirectionPicker(direction: $vm.direction)

                // Template picker
                VStack(alignment: .leading, spacing: 8) {
                    Text("Context Template")
                        .font(.subheadline.bold())
                    Picker("Template", selection: $vm.template) {
                        ForEach(TranslationTemplate.allCases, id: \.self) { t in
                            Text(t.displayName).tag(t)
                        }
                    }
                    .pickerStyle(.menu)

                    if vm.template == .custom {
                        TextField("Custom system prompt...", text: $vm.customPrompt, axis: .vertical)
                            .textFieldStyle(.roundedBorder)
                            .lineLimit(3...6)
                    }
                }

                // Input
                VStack(alignment: .leading, spacing: 8) {
                    Text("Input Text")
                        .font(.subheadline.bold())
                    TextEditor(text: $vm.inputText)
                        .frame(minHeight: 120)
                        .overlay(
                            RoundedRectangle(cornerRadius: 8)
                                .stroke(.quaternary)
                        )
                }

                // Translate button
                Button {
                    Task { await vm.translate() }
                } label: {
                    HStack {
                        if vm.isLoading {
                            ProgressView()
                                .tint(.white)
                        }
                        Text("Translate")
                            .bold()
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(vm.inputText.isEmpty ? Color.gray : Color.accentColor)
                    .foregroundStyle(.white)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                }
                .disabled(vm.inputText.isEmpty || vm.isLoading)

                // Result
                if let result = vm.result {
                    TranslationResultView(
                        original: result.originalText,
                        translated: result.translatedText,
                        creditsRemaining: result.creditsRemaining
                    )
                }

                // Error
                if let error = vm.error {
                    Text(error)
                        .font(.caption)
                        .foregroundStyle(.red)
                        .padding()
                }
            }
            .padding()
        }
        .navigationTitle("Text Translate")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button("Clear") { vm.clear() }
            }
        }
    }
}
