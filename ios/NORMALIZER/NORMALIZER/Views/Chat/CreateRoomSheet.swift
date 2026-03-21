import SwiftUI

struct CreateRoomSheet: View {
    @Environment(\.dismiss) private var dismiss
    @State private var name = ""
    @State private var isPublic = false

    let onCreate: (String, Bool) -> Void

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Room Name", text: $name)
                }

                Section {
                    Toggle("Public Room", isOn: $isPublic)
                } footer: {
                    Text("Public rooms can be joined by anyone with a link.")
                }
            }
            .navigationTitle("Create Room")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Create") {
                        onCreate(name, isPublic)
                    }
                    .disabled(name.trimmingCharacters(in: .whitespaces).isEmpty)
                }
            }
        }
        .presentationDetents([.medium])
    }
}
