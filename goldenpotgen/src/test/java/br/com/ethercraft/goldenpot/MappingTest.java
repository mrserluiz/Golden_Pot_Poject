package br.com.ethercraft.goldenpot;
import java.nio.file.*;
import java.util.*;
import com.google.gson.*;
public final class MappingTest {
 static void check(boolean ok,String message){if(!ok)throw new AssertionError(message);}
 public static void main(String[] args)throws Exception{
  Path base=Path.of(args[0]),temp=Files.createTempDirectory("gpg-mapping-test-"),root=temp.resolve("plugin"),geyser=temp.resolve("Geyser");
  Files.createDirectories(root);
  MappingInstaller.prepare(root,n->{try{return Files.newInputStream(base.resolve("resources").resolve(n));}catch(Exception e){throw new RuntimeException(e);}});
  MappingInstaller.install(root,geyser,System.out::println);
  Path target=geyser.resolve("custom_mappings/goldenpotgen_item.json");byte[] first=Files.readAllBytes(target);
  MappingInstaller.install(root,geyser,System.out::println);check(Arrays.equals(first,Files.readAllBytes(target)),"Repeated install changed output");
  var source=MappingInstaller.read(root.resolve("sources/mappings/geyser_item_mappings.json"));
  Path existing=geyser.resolve("custom_mappings/existing.json");Files.write(existing,Resources.json(source));byte[] existingBytes=Files.readAllBytes(existing);
  MappingInstaller.install(root,geyser,System.out::println);check(MappingInstaller.read(target).getAsJsonObject("items").isEmpty(),"Existing mappings duplicated");check(Arrays.equals(existingBytes,Files.readAllBytes(existing)),"Existing file overwritten");
  Files.delete(existing);MappingInstaller.install(root,geyser,System.out::println);
  String edit=Files.readString(target)+"\n ";Files.writeString(target,edit);MappingInstaller.install(root,geyser,System.out::println);check(Files.readString(target).equals(edit),"Admin modification overwritten");
  Path block=geyser.resolve("custom_mappings/goldenpotgen_block.json");check(MappingInstaller.read(block).getAsJsonObject("blocks").getAsJsonObject("minecraft:light").getAsJsonObject("state_overrides").size()==16,"Crop states lost");
  var generated=Resources.load(base.resolve("test-output/generated/EtherTexture-Bedrock-GoldenPotGen.mcpack"));
  check(Resources.object(new String(generated.get("textures/item_texture.json"))).getAsJsonObject("texture_data").has("ether.item_custom"),"Official pickaxe icon missing");
  check(MappingInstaller.read(base.resolve("test-output/reports/mapping-assets.json")).get("missing_icon_count").getAsInt()==65,"Unexpected missing count");
  System.out.println("PASS: repeat install, duplicate suppression, user-file preservation, admin edits, 16 crop states, official pickaxe repair, recursive asset audit");
 }
}
