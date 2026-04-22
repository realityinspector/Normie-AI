#!/usr/bin/env ruby
$LOAD_PATH.unshift(*Dir.glob(File.expand_path("~/.gem/ruby/*/gems/*/lib")))
require "xcodeproj"

PROJECT_PATH = File.expand_path(
  "../ios/NORMALIZER/NORMALIZER.xcodeproj",
  File.dirname(File.expand_path(__FILE__))
)

project = Xcodeproj::Project.open(PROJECT_PATH)
test_target = project.targets.find { |t| t.name == "NORMALIZERUITests" }
raise "UITest target missing" unless test_target

test_target.build_configurations.each do |config|
  bs = config.build_settings
  bs["PRODUCT_NAME"] = "$(TARGET_NAME)"
  bs["INFOPLIST_KEY_CFBundleDisplayName"] = "NORMALIZERUITests"
  bs["SWIFT_EMIT_LOC_STRINGS"] = "NO"
  bs["DEBUG_INFORMATION_FORMAT"] = "dwarf"
  bs["MTL_FAST_MATH"] = "YES"
  bs["GCC_C_LANGUAGE_STANDARD"] = "gnu17"
  bs["CLANG_CXX_LANGUAGE_STANDARD"] = "gnu++20"
end

project.save
puts "Patched NORMALIZERUITests build settings."
