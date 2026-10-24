package br.com.ethercraft.goldenpot;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;
import java.io.*;
public final class ResourceTest {
 static void require(boolean value,String message){if(!value)throw new AssertionError(message);}
 public static void main(String[] args)throws Exception{
  Path base=Path.of(args[0]),root=base.resolve("test-output");Files.createDirectories(root);
  Resources.prepare(root,name->{try{return Files.newInputStream(base.resolve("resources").resolve(name));}catch(IOException ex){throw new UncheckedIOException(ex);}},true);
  var j=Resources.load(root.resolve("generated/EtherTexture-Java-GoldenPotGen.zip"));
  var b=Resources.load(root.resolve("generated/EtherTexture-Bedrock-GoldenPotGen.mcpack"));
  var j0=Resources.load(base.resolve("resources/packs/java-base.zip"));var b0=Resources.load(base.resolve("resources/packs/bedrock-base.zip"));
  for(var e:j0.entrySet())require(Arrays.equals(e.getValue(),j.get(e.getKey())),"Java original changed: "+e.getKey());
  for(var e:b0.entrySet())if(!Set.of("manifest.json","textures/terrain_texture.json","textures/item_texture.json").contains(e.getKey()))require(Arrays.equals(e.getValue(),b.get(e.getKey())),"Bedrock original changed: "+e.getKey());
  for(String atlas:List.of("terrain_texture","item_texture")){
   String key="textures/"+atlas+".json";var before=Resources.object(new String(b0.get(key))).getAsJsonObject("texture_data");var after=Resources.object(new String(b.get(key))).getAsJsonObject("texture_data");
   for(var e:before.entrySet())require(e.getValue().equals(after.get(e.getKey())),"Atlas entry changed: "+e.getKey());
  }
  require(Arrays.equals(j.get("assets/goldenpot/textures/block/ambrosio_ore.png"),b.get("textures/goldenpot/ambrosio_ore.png")),"Cross-edition PNG mismatch");
  byte[] first=Files.readAllBytes(root.resolve("generated/EtherTexture-Java-GoldenPotGen.zip"));
  Resources.prepare(root,name->{try{return Files.newInputStream(base.resolve("resources").resolve(name));}catch(IOException ex){throw new UncheckedIOException(ex);}},true);
  require(Arrays.equals(first,Files.readAllBytes(root.resolve("generated/EtherTexture-Java-GoldenPotGen.zip"))),"Non-deterministic rebuild");
  Map<String,byte[]> conflict=new TreeMap<>();conflict.put("test",new byte[]{1});boolean failed=false;
  try{Resources.add(conflict,"test",new byte[]{2});}catch(IOException e){failed=true;}require(failed,"Conflicting resource silently overwritten");
  Path unsafe=root.resolve("unsafe.zip");try(ZipOutputStream out=new ZipOutputStream(Files.newOutputStream(unsafe))){out.putNextEntry(new ZipEntry("../escape"));out.write(1);out.closeEntry();}
  failed=false;try{Resources.load(unsafe);}catch(IOException e){failed=true;}require(failed,"Zip traversal accepted");Files.delete(unsafe);
  for(var entries:List.of(j,b))for(var e:entries.entrySet())if(e.getKey().endsWith(".json"))com.google.gson.JsonParser.parseString(new String(e.getValue(),java.nio.charset.StandardCharsets.UTF_8));
  System.out.println("PASS: source preservation, both atlases preserved, same official PNG, deterministic rebuild, conflict rejection, ZIP traversal rejection, JSON syntax. Java="+j.size()+" Bedrock="+b.size());
 }
}
