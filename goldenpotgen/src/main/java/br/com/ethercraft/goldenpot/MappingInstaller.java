package br.com.ethercraft.goldenpot;
import com.google.gson.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.function.*;

/** Uses Geyser's supported JSON directory before registry initialization. */
final class MappingInstaller {
 static final List<String> KINDS=List.of("item","block","skull","waypoint_style");
 static String section(String kind){return switch(kind){case "item"->"items";case "block"->"blocks";case "skull"->"skulls";default->"waypoint_styles";};}
 static JsonObject read(Path p)throws IOException{return Resources.object(Files.readString(p));}
 static void atomic(Path p,byte[] b)throws IOException{
  Files.createDirectories(p.getParent());Path t=Files.createTempFile(p.getParent(),"gpg-",".tmp");
  try{Files.write(t,b);try{Files.move(t,p,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);}catch(AtomicMoveNotSupportedException e){Files.move(t,p,StandardCopyOption.REPLACE_EXISTING);}}finally{Files.deleteIfExists(t);}
 }
 static String selector(String base,JsonObject row){
  // All legacy predicates affect the selector. Presentation fields do not.
  JsonObject key=new JsonObject();key.addProperty("base",base);
  for(String k:List.of("type","model","custom_model_data","damage_predicate","unbreakable","custom_model_data_float","custom_model_data_flag","custom_model_data_string","predicate"))if(row.has(k))key.add(k,row.get(k));
  return key.toString();
 }
 static void prepare(Path root,Function<String,InputStream> source)throws IOException{
  for(String kind:KINDS){String file="geyser_"+kind+"_mappings.json";Path p=root.resolve("sources/mappings/"+file);
   if(!Files.exists(p)){try(InputStream in=source.apply("mappings/"+file)){if(in==null)throw new IOException("Missing mapping: "+file);atomic(p,in.readAllBytes());}}
   JsonObject value=read(p);if(!value.has("format_version")||!value.has(section(kind)))throw new IOException("Invalid mapping: "+p);
  }
 }
 static String install(Path root,Path geyser,Consumer<String> log)throws IOException{
  Path directory=geyser.resolve("custom_mappings");Files.createDirectories(directory);
  JsonArray report=new JsonArray();int exported=0,skipped=0,conflicts=0;
  for(String kind:KINDS){
   String sec=section(kind),name="goldenpotgen_"+kind+".json";Path target=directory.resolve(name),receipt=root.resolve("mapping-receipts/"+name);
   // The last bytes written are the ownership receipt. Never overwrite user edits.
   if(Files.exists(target)&&(!Files.exists(receipt)||!Arrays.equals(Files.readAllBytes(target),Files.readAllBytes(receipt)))){
    report.add("Preserved modified or unowned file: "+target);conflicts++;continue;
   }
   Map<String,List<JsonElement>> occupied=new HashMap<>();
   try(var paths=Files.walk(directory)){
    for(Path p:paths.filter(f->f.toString().endsWith(".json")&&!f.equals(target)).sorted().toList()){
     JsonObject doc;
     try{doc=read(p);}catch(Exception e){throw new IOException("Cannot inspect existing mapping "+p,e);}
     if(!doc.has(sec))continue;
     JsonObject values=doc.getAsJsonObject(sec);
     for(var entry:values.entrySet()){
      if(kind.equals("item"))for(JsonElement row:entry.getValue().getAsJsonArray())occupied.computeIfAbsent(selector(entry.getKey(),row.getAsJsonObject()),k->new ArrayList<>()).add(row);
      else occupied.computeIfAbsent(entry.getKey(),k->new ArrayList<>()).add(entry.getValue());
     }
    }
   }
   JsonObject original=read(root.resolve("sources/mappings/geyser_"+kind+"_mappings.json"));
   JsonObject out=original.deepCopy(),values=new JsonObject();out.add(sec,values);
   for(var entry:original.getAsJsonObject(sec).entrySet()){
    if(kind.equals("item")){
     JsonArray kept=new JsonArray();
     for(JsonElement row:entry.getValue().getAsJsonArray()){
      String key=selector(entry.getKey(),row.getAsJsonObject());List<JsonElement> old=occupied.get(key);
      if(old==null){kept.add(row);occupied.put(key,new ArrayList<>(List.of(row)));exported++;}
      else{skipped++;if(old.stream().anyMatch(v->!v.equals(row))){report.add("Existing selector kept: "+key);conflicts++;}}
     }
     if(!kept.isEmpty())values.add(entry.getKey(),kept);
    }else{
     List<JsonElement> old=occupied.get(entry.getKey());
     if(old==null){values.add(entry.getKey(),entry.getValue());exported++;}
     else{skipped++;if(old.stream().anyMatch(v->!v.equals(entry.getValue()))){report.add("Existing block/key kept: "+entry.getKey());conflicts++;}}
    }
   }
   byte[] data=Resources.json(out);atomic(target,data);atomic(receipt,data);
  }
  JsonObject summary=new JsonObject();summary.addProperty("exported",exported);summary.addProperty("skipped",skipped);summary.addProperty("conflicts",conflicts);summary.add("details",report);
  atomic(root.resolve("reports/mapping-install.json"),Resources.json(summary));
  String result="exported="+exported+", skipped="+skipped+", conflicts="+conflicts;log.accept("Geyser mappings: "+result+" (restart required after changes)");return result;
 }
 static void audit(Path root,Map<String,byte[]> javaPack,Map<String,byte[]> bedrock)throws IOException{
  JsonObject atlas=Resources.object(new String(bedrock.get("textures/item_texture.json"),StandardCharsets.UTF_8)).getAsJsonObject("texture_data");
  Set<String> icons=new TreeSet<>();collect(read(root.resolve("sources/mappings/geyser_item_mappings.json")),icons);
  JsonArray missing=new JsonArray();for(String icon:icons)if(!atlas.has(icon))missing.add(icon);
  JsonObject report=new JsonObject();report.addProperty("unique_icons",icons.size());report.addProperty("missing_icon_count",missing.size());report.add("missing_icons",missing);
  report.addProperty("note","Mappings are preserved. Missing assets are not replaced with generic art. Runtime Geyser/client validation remains required.");
  atomic(root.resolve("reports/mapping-assets.json"),Resources.json(report));
 }
 static void collect(JsonElement v,Set<String> icons){
  if(v.isJsonObject()){JsonObject o=v.getAsJsonObject();if(o.has("icon")&&o.get("icon").isJsonPrimitive())icons.add(o.get("icon").getAsString());for(var e:o.entrySet())collect(e.getValue(),icons);}
  else if(v.isJsonArray())for(JsonElement e:v.getAsJsonArray())collect(e,icons);
 }
 static void repairOfficialPickaxe(Map<String,byte[]> j,Map<String,byte[]> b)throws IOException{
  byte[] png=j.get("assets/ether/textures/item/custom.png");if(png==null)return;
  String key="textures/item_texture.json";JsonObject doc=Resources.object(new String(b.get(key),StandardCharsets.UTF_8));JsonObject atlas=doc.getAsJsonObject("texture_data");
  if(atlas.has("ether.item_custom"))return;
  Resources.add(b,"textures/goldenpot/official_celestial_pickaxe.png",png);
  atlas.add("ether.item_custom",Resources.object("{\"textures\":\"textures/goldenpot/official_celestial_pickaxe\"}"));b.put(key,Resources.json(doc));
 }
}
