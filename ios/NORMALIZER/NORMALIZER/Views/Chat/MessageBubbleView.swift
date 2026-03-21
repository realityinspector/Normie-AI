import SwiftUI

struct MessageBubbleView: View {
    let message: ChatMessage
    let isFromCurrentUser: Bool

    var body: some View {
        HStack {
            if isFromCurrentUser { Spacer(minLength: 60) }

            VStack(alignment: isFromCurrentUser ? .trailing : .leading, spacing: 4) {
                if !isFromCurrentUser {
                    Text(message.senderName)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }

                Text(message.originalText)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 10)
                    .background(isFromCurrentUser ? Color.accentColor : Color(.systemGray5))
                    .foregroundStyle(isFromCurrentUser ? .white : .primary)
                    .clipShape(RoundedRectangle(cornerRadius: 18))

                Text(message.createdAt, style: .time)
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
            }

            if !isFromCurrentUser { Spacer(minLength: 60) }
        }
    }
}
