import SwiftUI

struct DirectionPicker: View {
    @Binding var direction: TranslationDirection

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Direction")
                .font(.subheadline.bold())
            Picker("Direction", selection: $direction) {
                ForEach(TranslationDirection.allCases, id: \.self) { d in
                    Text(d.displayName).tag(d)
                }
            }
            .pickerStyle(.segmented)
        }
    }
}
